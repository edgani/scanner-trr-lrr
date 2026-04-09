from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any
import re

from config.weights import EM_ROTATION_WEIGHTS

from engines.quad_state_engine import QuadStateEngine
from engines.tactical_weather_engine import TacticalWeatherEngine
from engines.shock_override_engine import ShockOverrideEngine
from engines.market_health_engine import MarketHealthEngine
from engines.positioning_engine import PositioningEngine
from engines.vix_bucket_engine import VIXBucketEngine
from engines.scenario_discovery_engine import ScenarioDiscoveryEngine
from engines.execution_bridge_engine import ExecutionBridgeEngine
from engines.validation_engine import ValidationEngine
from engines.news_event_engine import NewsEventEngine
from engines.historical_analog_engine import HistoricalAnalogEngine
from engines.policy_playbook_engine import PolicyPlaybookEngine
from engines.rotation_engine import RotationEngine
from engines.checklist_engine import build_global_checklist
from engines.risk_range_engine import RiskRangeEngine
from engines.crash_meter_engine import CrashMeterEngine


def _resolve_regime_stack(quad: dict, weather: dict) -> dict:
    structural_quad = quad.get('structural_quad', quad.get('current_quad', 'Q?'))
    monthly_quad = quad.get('monthly_quad', structural_quad)
    divergence_state = quad.get('divergence_state', 'aligned' if monthly_quad == structural_quad else 'divergent')
    weather_score = float(weather.get('score', 0.5))
    trade_state = weather.get('trade_state', 'balanced')
    tail_state = weather.get('tail_state', 'neutral')

    if divergence_state == 'aligned':
        dominant_horizon = 'aligned'
        execution_bias = f'aligned_{structural_quad.lower()}'
        operating_regime = f'Aligned {structural_quad}'
    else:
        if weather_score >= 0.58 and trade_state == 'supportive' and tail_state != 'stressed':
            dominant_horizon = 'monthly'
            execution_bias = f'tactical_{monthly_quad.lower()}_inside_{structural_quad.lower()}'
        elif weather_score <= 0.42 or tail_state == 'stressed':
            dominant_horizon = 'structural'
            execution_bias = f'structural_{structural_quad.lower()}_dominant'
        else:
            dominant_horizon = 'balanced'
            execution_bias = f'mixed_{monthly_quad.lower()}_inside_{structural_quad.lower()}'
        operating_regime = f'Monthly {monthly_quad} inside Structural {structural_quad}'

    return {
        'structural': {
            'quad': structural_quad,
            'next_quad': quad.get('structural_next_quad', quad.get('next_quad', 'Q?')),
            'probs': quad.get('structural_probs', quad.get('probs', {})),
            'confidence': quad.get('structural_confidence', quad.get('confidence', 0.0)),
            'g_core': quad.get('g_core', 0.0),
            'i_core': quad.get('i_core', 0.0),
            'p_core': quad.get('p_core', 0.0),
        },
        'monthly': {
            'quad': monthly_quad,
            'next_quad': quad.get('monthly_next_quad', monthly_quad),
            'probs': quad.get('monthly_probs', {}),
            'confidence': quad.get('monthly_confidence', 0.0),
            'g_core': quad.get('g_monthly_core', quad.get('g_core', 0.0)),
            'i_core': quad.get('i_monthly_core', quad.get('i_core', 0.0)),
            'p_core': quad.get('p_monthly_core', quad.get('p_core', 0.0)),
        },
        'signal': {
            'trade_state': trade_state,
            'trend_state': weather.get('trend_state', 'mixed'),
            'tail_state': tail_state,
            'weather_bias': weather.get('weather_bias', 'mixed'),
            'weather_score': weather_score,
        },
        'resolved': {
            'divergence_state': divergence_state,
            'operating_regime': operating_regime,
            'dominant_horizon': dominant_horizon,
            'execution_bias': execution_bias,
        },
    }



def _confidence_band(conf: float) -> str:
    conf = float(conf or 0.0)
    if conf < 0.20:
        return 'low'
    if conf < 0.40:
        return 'tentative'
    if conf < 0.60:
        return 'moderate'
    return 'high'


def _resolved_language(operating_regime: str, confidence: float) -> str:
    band = _confidence_band(confidence)
    prefix = {
        'low': 'Low-Conviction',
        'tentative': 'Tentative',
        'moderate': 'Moderate-Conviction',
        'high': 'High-Conviction',
    }[band]
    return f"{prefix} {operating_regime}"


def _breadth_state(score: float, narrow: float) -> str:
    score = float(score or 0.0)
    narrow = float(narrow or 0.0)
    if score >= 0.62 and narrow <= 0.42:
        return 'broad / healthy'
    if score >= 0.52 and narrow <= 0.58:
        return 'mixed but okay'
    if narrow >= 0.66:
        return 'narrow / fragile'
    return 'mixed / watch'


def _build_next_path(quad: dict, regime_stack: dict, weather: dict, shock: dict, news_state: dict, rotation: dict, em_rotation: dict, risk_summary: dict, features: dict, next_macro_summary: dict) -> dict:
    structural = regime_stack.get('structural', {}) or {}
    monthly = regime_stack.get('monthly', {}) or {}
    resolved = regime_stack.get('resolved', {}) or {}
    structural_quad = structural.get('quad', quad.get('current_quad', 'Q?'))
    monthly_quad = monthly.get('quad', structural_quad)
    structural_next = structural.get('next_quad', quad.get('next_quad', structural_quad))
    monthly_next = monthly.get('next_quad', monthly_quad)
    if structural_next == monthly_next:
        next_resolved_regime = f'Aligned {structural_next}'
    else:
        next_resolved_regime = f'Monthly {monthly_next} inside Structural {structural_next}'
    flip_hazard = float(quad.get('flip_hazard', 0.5))
    inflation_shock = float(features.get('macro', {}).get('inflation_shock', 0.0))
    slowdown_flags = float(features.get('macro', {}).get('slowdown_flags', 0.0))
    news_state_name = str((news_state or {}).get('state', 'quiet'))
    triggers = [
        f"Next macro: {next_macro_summary.get('headline', '-')}",
        'Breadth / credit confirmation',
        'USD and yields direction',
    ]
    if inflation_shock >= 0.20:
        triggers.insert(0, 'Inflation pulse holds / re-accelerates')
    if slowdown_flags >= 0.20:
        triggers.insert(0, 'Growth slowdown broadens')
    if news_state_name in {'war_oil', 'policy_pressure', 'china_false_dawn', 'carry_unwind'}:
        triggers.insert(0, f'News branch: {news_state_name}')

    invalidators = ['Breadth broadens against the branch', 'USD / rates reverse sharply', 'Cross-asset confirmation fails']
    if risk_summary.get('big_crash_state', 'calm') != 'calm':
        invalidators.append('Crash stress escalates faster than the branch assumes')

    continuation = f"If current regime persists: stay with {', '.join((rotation.get('resolved_rotation', {}) or {}).get('leaders', [])[:3]) or '-'}"
    monthly_fade = f"If monthly fades: rotate toward {', '.join((rotation.get('structural_rotation', {}) or {}).get('leaders', [])[:3]) or '-'}"
    structural_flip = f"If structural flips: next backbone likely {', '.join((rotation.get('next_rotation', {}) or {}).get('leaders', [])[:3]) or '-'}"

    market_routes = {
        'us': continuation,
        'ihsg': monthly_fade if 'IHSG' in ' '.join((rotation.get('next_rotation', {}) or {}).get('leaders', [])) else continuation,
        'fx': 'Watch carry vs funding winners / losers',
        'commodities': 'Watch energy vs gold vs defensives split',
        'crypto': 'Watch majors breadth vs tactical-only bounce',
    }

    structural_probs = structural.get('probs', {}) or {}
    monthly_probs = monthly.get('probs', {}) or {}
    structural_rank = sorted(structural_probs.items(), key=lambda kv: kv[1], reverse=True)[:2]
    monthly_rank = sorted(monthly_probs.items(), key=lambda kv: kv[1], reverse=True)[:2]
    return {
        'next_structural_quad': structural_next,
        'next_monthly_quad': monthly_next,
        'next_resolved_regime': next_resolved_regime,
        'flip_hazard': flip_hazard,
        'confidence_band': _confidence_band(max(float(structural.get('confidence', 0.0)), float(monthly.get('confidence', 0.0)))),
        'structural_candidates': [{'quad': q, 'prob': float(p)} for q, p in structural_rank],
        'monthly_candidates': [{'quad': q, 'prob': float(p)} for q, p in monthly_rank],
        'triggers': triggers[:5],
        'invalidators': invalidators[:4],
        'continuation_path': continuation,
        'monthly_fade_path': monthly_fade,
        'structural_flip_path': structural_flip,
        'market_routes': market_routes,
    }

def build_shared_core(features: dict, raw: dict) -> dict:
    quad = asdict(QuadStateEngine().run(features['macro']))
    weather = asdict(TacticalWeatherEngine().run(features['market'], features['breadth'], features['vol_credit']))
    shock = asdict(ShockOverrideEngine().run(features['scenario'], features['plumbing'], features['vol_credit']))
    health = MarketHealthEngine().run(features['market'])
    positioning = PositioningEngine().run(features['positioning'])
    vix_bucket = VIXBucketEngine().run(features['derivatives'])
    validation = ValidationEngine().run(raw.get('prices', {}))
    news_state = NewsEventEngine().run(raw.get('news', {}), features['market'], features['macro'])
    analogs = [asdict(x) for x in HistoricalAnalogEngine().run(features['macro'], features['market'], shock.get('state', 'normal'))]
    playbooks = PolicyPlaybookEngine().run(features['macro'], features['market'], features['plumbing'], shock.get('state', 'normal'))
    regime_stack = _resolve_regime_stack(quad, weather)
    em_rotation = _build_em_rotation(features['market'], validation, regime_stack, news_state)
    petrodollar = _build_petrodollar(features, news_state, regime_stack)
    rotation = RotationEngine().run(features['market'], em_rotation, regime_stack, news_state)
    scenario_cases = ScenarioDiscoveryEngine().run(quad, weather, shock, features.get('scenario', {}), playbooks, analogs, news_state)
    scenario_tab_impact_map = _build_scenario_tab_impact_map(scenario_cases)
    execution_mode = ExecutionBridgeEngine().run(quad, weather, shock, health, vix_bucket, positioning, features.get('derivatives', {}))
    global_checklist = build_global_checklist({}, features, news_state, em_rotation)

    macro_calendar_raw = (raw.get('macro_calendar') or {})
    macro_calendar = _select_engine_macro_events((macro_calendar_raw.get('all_events') or macro_calendar_raw.get('events') or []), limit=10)
    next_macro_summary = _summarize_next_macro(macro_calendar)
    macro_drivers = _build_top_drivers(features, news_state, macro_calendar)
    macro_risks = _build_top_risks(news_state, features)
    event_bubble = _build_ranked_event_bubble(macro_calendar, news_state, raw.get('events', []))
    risk_range = RiskRangeEngine().run(raw.get('prices', {}), features['market'], features['vol_credit'], positioning, features.get('derivatives', {}), shock)
    risk_summary = CrashMeterEngine().run(weather, shock, health, vix_bucket, positioning, features.get('derivatives', {}), features['market'])
    next_path = _build_next_path(quad, regime_stack, weather, shock, news_state, rotation, em_rotation, risk_summary, features, next_macro_summary)
    next_path['petrodollar_route'] = petrodollar.get('next_route', '-')
    next_path['em_next_route'] = em_rotation.get('next_route', '-')
    regime_stack['resolved']['confidence_band'] = _confidence_band(max(float(regime_stack['structural'].get('confidence', 0.0)), float(regime_stack['monthly'].get('confidence', 0.0))))
    regime_stack['resolved']['resolved_language'] = _resolved_language(regime_stack['resolved']['operating_regime'], max(float(regime_stack['structural'].get('confidence', 0.0)), float(regime_stack['monthly'].get('confidence', 0.0))))
    flow_stack = {
        'rotation': {
            'structural': rotation.get('structural_rotation', {}),
            'monthly': rotation.get('monthly_rotation', {}),
            'resolved': rotation.get('resolved_rotation', {}),
            'next': rotation.get('next_rotation', {}),
        },
        'em_rotation': em_rotation,
        'petrodollar': petrodollar,
    }

    breadth_snapshot = {
        'breadth_score': features.get('breadth', {}).get('breadth_score', 0.5),
        'sector_support_ratio': features.get('breadth', {}).get('sector_support_ratio', features.get('market', {}).get('sector_support_ratio', 0.5)),
        'narrow_leadership': features.get('breadth', {}).get('narrow_leadership', features.get('market', {}).get('narrow_leadership', 0.5)),
        'breadth_state': _breadth_state(features.get('breadth', {}).get('breadth_score', 0.5), features.get('breadth', {}).get('narrow_leadership', features.get('market', {}).get('narrow_leadership', 0.5))),
        'breadth_trend': features.get('market', {}).get('breadth_trend_state', 'fragile'),
    }

    integrity = {
        'macro_proxy_share': features.get('macro', {}).get('macro_proxy_share', 0.0),
        'macro_confidence_penalty': features.get('macro', {}).get('macro_confidence_penalty', 0.0),
        'breadth_quality': features.get('breadth', {}).get('breadth_score', 0.5),
        'crowding_proxy': positioning.get('crowding_proxy', positioning.get('crowding', 0.5)),
        'crowding_state': positioning.get('crowding_state', positioning.get('verdict', 'clean')),
        'derivatives_proxy_only': bool(features.get('derivatives', {}).get('is_proxy_only', True)),
        'positioning_proxy_only': bool(positioning.get('is_proxy_only', True)),
        'risk_range_anchor': risk_range.get('anchor_symbol', 'SPY'),
        'risk_range_state': risk_range.get('range_state', 'unknown'),
        'quad_divergence': regime_stack['resolved']['divergence_state'],
        'breadth_state': breadth_snapshot['breadth_state'],
        'breadth_trend': breadth_snapshot['breadth_trend'],
        'narrow_leadership': breadth_snapshot['narrow_leadership'],
    }

    return {
        'regime': quad,
        'regime_stack': regime_stack,
        'resolved_regime': regime_stack['resolved'],
        'next_path': next_path,
        'flow_stack': flow_stack,
        'weather': weather,
        'shock': shock,
        'health': health,
        'positioning': positioning,
        'vix_bucket': vix_bucket,
        'validation': validation,
        'news_state': news_state,
        'analogs': analogs,
        'historical_analog_state': {'top': analogs[0] if analogs else {}, 'consequence': (analogs[0].get('next_bias', '-') if analogs else '-')},
        'playbooks': playbooks,
        'rotation': rotation,
        'em_rotation': em_rotation,
        'scenario_flags': features.get('scenario', {}).get('flags', []),
        'petrodollar': petrodollar,
        'next_macro': macro_calendar,
        'next_macro_summary': next_macro_summary,
        'scenario_family': list(scenario_cases.keys())[:6],
        'what_if_matrix': {name: {'p': case.probability, 'desc': case.description, 'winners': case.winners, 'losers': case.losers, 'invalidators': case.invalidators} for name, case in scenario_cases.items()},
        'scenario_tab_impact_map': scenario_tab_impact_map,
        'execution_mode': execution_mode,
        'global_checklist': global_checklist,
        'integrity': integrity,
        'breadth_snapshot': breadth_snapshot,
        'risk_range': risk_range,
        'risk_summary': risk_summary,
        'tactical_components': {
            'trade_score': weather.get('trade_score', 0.5),
            'trend_score': weather.get('trend_score', 0.5),
            'tail_score': weather.get('tail_score', 0.5),
            'cross_asset_confirm': weather.get('cross_asset_confirm', 0.5),
            'weather_score': weather.get('score', 0.5),
        },
        'macro_impact_global': {
            'now': 'Macro global sekarang dibaca lewat growth, inflasi, yields, USD, breadth, sama shock geopolitik.',
            'best_expression': rotation.get('best_beneficiary_why', 'Fokus ke market yang backdrop-nya paling sinkron sama regime sekarang.'),
            'forward_branch': next_macro_summary.get('impact_path', 'Kalau breadth dan credit confirm, leadership bisa makin lebar. Kalau shock naik, market defensif lagi.'),
            'invalidator': 'USD spike, yields naik lagi, breadth makin sempit.',
            'drivers': macro_drivers,
            'risks': macro_risks,
            'trigger': 'Breadth membaik + USD/yields reda + credit tidak memburuk.',
            'confidence': max(float(regime_stack['structural'].get('confidence', 0.0)), float(regime_stack['monthly'].get('confidence', 0.0))),
            'next_macro_focus': next_macro_summary.get('headline', '-'),
            'next_macro_note': next_macro_summary.get('note', '-'),
            'next_macro_countdown': next_macro_summary.get('countdown', '-'),
        },
        'top_drivers': macro_drivers,
        'top_risks': macro_risks,
        'event_bubble': event_bubble,
        'safe_harbor': rotation.get('safe_harbor', 'USD'),
        'best_beneficiary': rotation.get('best_beneficiary', 'XAUUSD'),
        'status_ribbon': {
            'current_quad': quad.get('current_quad', 'Q?'),
            'structural_quad': regime_stack['structural']['quad'],
            'monthly_quad': regime_stack['monthly']['quad'],
            'operating_regime': regime_stack['resolved']['operating_regime'],
            'dominant_horizon': regime_stack['resolved']['dominant_horizon'],
            'resolved_language': regime_stack['resolved'].get('resolved_language', regime_stack['resolved']['operating_regime']),
            'confidence_band': regime_stack['resolved'].get('confidence_band', 'low'),
            'confidence': max(float(regime_stack['structural'].get('confidence', 0.0)), float(regime_stack['monthly'].get('confidence', 0.0))),
            'health': health.get('verdict', 'mixed'),
            'safe_harbor': rotation.get('safe_harbor', 'USD'),
            'best_beneficiary': rotation.get('best_beneficiary', 'XAUUSD'),
            'em_rotation': em_rotation.get('state', 'selective'),
            'risk_off': risk_summary.get('risk_off_state', 'calm'),
            'crash': risk_summary.get('crash_state', 'calm'),
            'range': risk_range.get('range_state', 'unknown'),
            'stretch': risk_range.get('stretch_state', 'neutral'),
            'breadth_state': breadth_snapshot['breadth_state'],
            'breadth_trend': breadth_snapshot['breadth_trend'],
            'narrow_leadership': breadth_snapshot['narrow_leadership'],
        },
        'conflict_map': {'monthly_vs_structural': regime_stack['resolved']['divergence_state'], 'petrodollar': ('elevated' if float(features.get('scenario', {}).get('petrodollar_shock', 0.0)) >= 0.62 else 'normal')},
        'confirmation_map': {'signal_confirms': regime_stack['resolved']['dominant_horizon'], 'em_rotation': em_rotation.get('resolved_state', em_rotation.get('state', 'selective')), 'next_resolved_regime': next_path.get('next_resolved_regime', '-')},
    }


def _build_em_rotation(market: dict, validation: dict, regime_stack: dict, news_state: dict | None = None) -> dict:
    structural_quad = regime_stack.get('structural', {}).get('quad', 'Q?')
    monthly_quad = regime_stack.get('monthly', {}).get('quad', structural_quad)
    resolved = regime_stack.get('resolved', {}) or {}
    usd_relief = max(0.0, -float(market.get('dxy_1m', 0.0)))
    broad_em = max(0.0, float(market.get('eem_rel_1m', 0.0)))
    broad_em_3m = max(0.0, float(market.get('eem_rel_3m', 0.0)))
    ihsg = max(0.0, float(market.get('ihsg_rel_1m', 0.0)))
    breadth = float(market.get('breadth_health', 0.5))
    duration = max(0.0, float(market.get('tlt_1m', 0.0)))
    commodity_exporter = max(0.0, float(market.get('escape_wti', 0.0)))
    importer_pain = max(0.0, float(market.get('dxy_1m', 0.0))) * 0.5 + max(0.0, -ihsg) * 0.5

    structural_map = {'Q1': 0.52, 'Q2': 0.62, 'Q3': 0.50, 'Q4': 0.34}
    monthly_map = {'Q1': 0.54, 'Q2': 0.66, 'Q3': 0.58, 'Q4': 0.30}

    structural_score = max(0.0, min(1.0,
        EM_ROTATION_WEIGHTS['structural'] * structural_map.get(structural_quad, 0.45)
        + EM_ROTATION_WEIGHTS['usd_relief'] * min(1.0, usd_relief / 0.03)
        + EM_ROTATION_WEIGHTS['broad_em'] * min(1.0, (broad_em + broad_em_3m) / 0.08)
        + EM_ROTATION_WEIGHTS['breadth'] * breadth
        + EM_ROTATION_WEIGHTS['duration'] * min(1.0, duration / 0.04)
    ))
    monthly_score = max(0.0, min(1.0,
        EM_ROTATION_WEIGHTS['monthly'] * monthly_map.get(monthly_quad, 0.45)
        + EM_ROTATION_WEIGHTS['usd_relief'] * min(1.0, usd_relief / 0.03)
        + EM_ROTATION_WEIGHTS['commodity_exporter'] * min(1.0, (ihsg + commodity_exporter) / 0.08)
        + EM_ROTATION_WEIGHTS['breadth'] * breadth
    ))

    if resolved.get('dominant_horizon') == 'monthly':
        resolved_score = 0.40 * structural_score + 0.60 * monthly_score
    elif resolved.get('dominant_horizon') == 'structural':
        resolved_score = 0.70 * structural_score + 0.30 * monthly_score
    else:
        resolved_score = 0.55 * structural_score + 0.45 * monthly_score

    state = 'strong' if structural_score >= 0.70 else ('early' if structural_score >= 0.56 else ('selective' if structural_score >= 0.44 else 'not yet'))
    monthly_state = 'strong' if monthly_score >= 0.70 else ('early' if monthly_score >= 0.56 else ('selective' if monthly_score >= 0.44 else 'not yet'))
    resolved_state = 'strong' if resolved_score >= 0.70 else ('early' if resolved_score >= 0.56 else ('selective' if resolved_score >= 0.44 else 'not yet'))
    exporter_vs_importer = 'exporters favored' if commodity_exporter >= importer_pain else 'importers under pressure'
    next_route = 'broad EM catch-up' if resolved_score >= 0.62 else ('selective exporters only' if monthly_score >= structural_score else 'safe EM carry only')
    why = validation.get('summary', 'EM rotation baca dari EEM, IHSG, breadth AS, dan USD.')
    why += f" Structural {structural_quad}, monthly {monthly_quad}, dominant {resolved.get('dominant_horizon', 'aligned')}."
    return {
        'score': resolved_score, 'state': resolved_state,
        'structural_score': structural_score, 'monthly_score': monthly_score, 'resolved_score': resolved_score,
        'structural_state': state, 'monthly_state': monthly_state, 'resolved_state': resolved_state, 'why': why,
        'structural_rotation': {'state': state, 'leaders': ['Commodity exporters', 'High-quality Asia'] if structural_score >= 0.5 else ['USD-sensitive defensives'], 'why': 'Structural EM route set by dollar, breadth, and broad EM relative strength.'},
        'monthly_rotation': {'state': monthly_state, 'leaders': ['IHSG/resource beta', 'Selective exporters'] if monthly_score >= 0.5 else ['Safe carry / hedges'], 'why': 'Monthly EM route set by tactical exporter pulse and local market confirmation.'},
        'resolved_rotation': {'state': resolved_state, 'leaders': ['Exporters', 'Selective carry'] if resolved_score >= 0.5 else ['Defensive carry'], 'why': 'Resolved EM playbook blends structural route and monthly pulse.'},
        'exporters_vs_importers': exporter_vs_importer,
        'dollar_funding_stress': round(max(0.0, float(market.get('dxy_1m', 0.0))) + max(0.0, -broad_em), 3),
        'next_route': next_route,
    }


def _build_petrodollar(features: dict, news_state: dict | None, regime_stack: dict) -> dict:
    scenario = features.get('scenario', {}) or {}
    market = features.get('market', {}) or {}
    score = float(scenario.get('petrodollar_shock', 0.0) or 0.0)
    importer_pain = float(scenario.get('em_importer_pain', 0.0) or 0.0)
    exporter_benefit = float(scenario.get('petro_exporter_benefit', 0.0) or 0.0)
    chokepoint = float(scenario.get('shipping_chokepoint', 0.0) or 0.0)
    funding = float(scenario.get('dollar_liquidity_squeeze', 0.0) or 0.0)
    state = 'elevated' if score >= 0.62 else ('watch' if score >= 0.48 else 'normal')
    structural_quad = regime_stack.get('structural', {}).get('quad', 'Q?')
    monthly_quad = regime_stack.get('monthly', {}).get('quad', structural_quad)
    chain = [
        'oil / shipping pulse',
        'USD funding pressure',
        'EM importer pain vs exporter benefit',
        'gold / energy / shipping winners',
        'cyclical breadth conflict',
    ]
    next_route = 'energy/gold lead then importer pain broadens' if state != 'normal' else 'petrodollar branch dormant'
    return {
        'score': score,
        'state': state,
        'em_importer_pain': importer_pain,
        'petro_exporter_benefit': exporter_benefit,
        'shipping_chokepoint': chokepoint,
        'dollar_funding_stress': funding,
        'active_if': f'structural {structural_quad} / monthly {monthly_quad}',
        'chain': chain,
        'next_route': next_route,
        'winners': ['Energy', 'Gold', 'Petro FX', 'Shipping'],
        'losers': ['Oil importers', 'Broad cyclicals', 'Fragile EM FX'],
    }


def _build_scenario_tab_impact_map(cases: dict) -> list[dict]:
    rows = []
    for name, case in list(cases.items())[:8]:
        lower = name.lower()
        if 'petrodollar' in lower or 'oil' in lower or 'war' in lower:
            impact = {'US': 'mixed', 'IHSG': 'selective+', 'FX': 'USD/petro FX+', 'Commodities': 'bullish', 'Crypto': 'fragile', 'EM': 'split', 'Spillover': 'energy-first'}
        elif 'carry unwind' in lower or 'dollar squeeze' in lower:
            impact = {'US': 'defensive', 'IHSG': 'bearish', 'FX': 'USD+', 'Commodities': 'gold>', 'Crypto': 'bearish', 'EM': 'bearish', 'Spillover': 'funding-stress'}
        elif 'broadening' in lower:
            impact = {'US': 'bullish', 'IHSG': 'bullish', 'FX': 'carry+', 'Commodities': 'mixed+', 'Crypto': 'bullish', 'EM': 'broadening', 'Spillover': 'breadth-expands'}
        elif 'historical' in lower or 'analog' in lower:
            impact = {'US': 'analog', 'IHSG': 'analog', 'FX': 'analog', 'Commodities': 'analog', 'Crypto': 'analog', 'EM': 'analog', 'Spillover': 'analog'}
        else:
            impact = {'US': 'mixed', 'IHSG': 'mixed', 'FX': 'mixed', 'Commodities': 'mixed', 'Crypto': 'mixed', 'EM': 'mixed', 'Spillover': 'mixed'}
        rows.append({'scenario': name, 'probability': round(100 * float(case.probability), 1), **impact})
    return rows


_ENGINE_FAMILIES = {'policy', 'inflation', 'inflation_pipeline', 'labor', 'growth', 'consumer', 'activity', 'labor_cost'}


def _select_engine_macro_events(events: list[dict], limit: int = 10) -> list[dict]:
    if not events:
        return []

    now = datetime.now(timezone.utc)

    def score(item: dict) -> tuple[int, int, str]:
        dt = _parse_dt(item.get('event_dt'))
        soon_penalty = 999999
        if dt is not None:
            soon_penalty = max(0, int((dt - now).total_seconds() // 3600))
        family = str(item.get('family', 'other'))
        family_bonus = 20 if family in _ENGINE_FAMILIES else 0
        return (int(item.get('priority', 0)) + family_bonus, -soon_penalty, str(item.get('title', '')).lower())

    candidates = [x for x in events if _parse_dt(x.get('event_dt')) is not None]
    candidates.sort(key=score, reverse=True)

    selected: list[dict] = []
    seen_titles = set()
    seen_families = set()

    for item in candidates:
        family = str(item.get('family', 'other'))
        title = str(item.get('title', '')).strip().lower()
        if not title or family in seen_families:
            continue
        selected.append(item)
        seen_titles.add(title)
        if family in _ENGINE_FAMILIES:
            seen_families.add(family)
        if len(selected) >= min(limit, 6):
            break

    for item in candidates:
        title = str(item.get('title', '')).strip().lower()
        if not title or title in seen_titles:
            continue
        selected.append(item)
        seen_titles.add(title)
        if len(selected) >= limit:
            break

    selected.sort(key=lambda x: (_parse_dt(x.get('event_dt')) or datetime.max.replace(tzinfo=timezone.utc), -int(x.get('priority', 0))))
    return selected[:limit]

def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _format_countdown(dt: datetime | None) -> str:
    if not dt:
        return '-'
    now = datetime.now(timezone.utc)
    secs = int((dt - now).total_seconds())
    if secs <= 0:
        return 'Released / started'
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    if days > 0:
        return f"T-{days}d {hours}h"
    if hours > 0:
        return f"T-{hours}h {mins}m"
    return f"T-{mins}m"


def _summarize_next_macro(events: list[dict]) -> dict:
    if not events:
        return {
            'headline': 'Belum dapat next macro catalyst resmi.',
            'note': 'Fallback ke headline/news confirmation dan price action.',
            'impact_path': 'Kalau data berikutnya lebih panas, yields/USD bisa reprice. Kalau lebih dingin, relief bisa melebar.',
            'countdown': '-',
            'family': '-',
        }
    nxt = events[0]
    family = str(nxt.get('family', 'macro'))
    title = str(nxt.get('title', 'Next macro event'))
    when = str(nxt.get('label', ''))
    dt = _parse_dt(nxt.get('event_dt'))
    path_map = {
        'inflation': 'Data inflasi berikutnya bisa langsung ngubah rates path, DXY, growth-stock breadth, sama gold/crypto reaction.',
        'inflation_pipeline': 'Pipeline inflation data bisa mengubah pricing CPI/PCE berikutnya dan cepat nembus ke yields, USD, dan commodities.',
        'labor': 'Data labor berikutnya bisa geser soft-landing vs slowdown odds, kecil-besar risk-on, dan front-end rate cuts pricing.',
        'growth': 'Data growth berikutnya bisa geser quad/nowcast dan nentuin apakah cyclical breadth ikut confirm atau malah gagal.',
        'policy': 'Policy catalyst berikutnya bisa reset discount-rate, duration appetite, USD, dan seluruh high-beta expressions.',
        'consumer': 'Data consumer berikutnya bisa ngeset ulang demand durability vs slowdown risk dan spillover ke rates serta cyclicals.',
        'activity': 'Activity survey berikutnya bisa jadi early branch detector buat growth re-accel versus growth scare.',
    }
    return {
        'headline': title,
        'note': when,
        'impact_path': path_map.get(family, 'Catalyst berikutnya bisa ubah branch lewat rates, USD, breadth, dan cross-asset confirmation.'),
        'countdown': _format_countdown(dt),
        'family': family,
        'event_dt': nxt.get('event_dt', ''),
    }


def _build_top_drivers(features: dict, news_state: dict, macro_calendar: list[dict]) -> list[str]:
    drivers = [
        'Growth trend',
        'Inflation trend',
        'Rates / duration',
        'USD / DXY',
        'Breadth / small caps',
    ]
    if news_state.get('display_state') not in {None, 'Quiet', 'quiet'}:
        drivers.append(f"News catalyst: {news_state.get('display_state')}")
    return _dedupe_texts(drivers)[:6]


def _build_top_risks(news_state: dict, features: dict) -> list[str]:
    risks = [
        'Yield spike',
        'USD spike',
        'Credit stress',
        'Breadth sempit',
    ]
    if float(news_state.get('war_oil_hazard', 0.0)) >= 0.35:
        risks.insert(0, 'War / oil shock')
    if float(news_state.get('policy_pressure_hazard', 0.0)) >= 0.35:
        risks.insert(0, 'Policy pressure / long-end stress')
    if float(features.get('macro', {}).get('inflation_shock', 0.0)) >= 0.25:
        risks.append('Inflation re-acceleration')
    return _dedupe_texts(risks)[:6]


def _headline_priority(title: str) -> tuple[int, str, str]:
    lower = title.lower()
    rules = [
        (r'cpi|inflation|pce|ppi', 95, 'inflation', 'high'),
        (r'payroll|employment|jobless|jolts|labor', 92, 'labor', 'high'),
        (r'gdp|growth|recession|soft landing', 90, 'growth', 'high'),
        (r'fed|fomc|rates|yield|treasury', 88, 'policy', 'high'),
        (r'oil|hormuz|iran|middle east|war', 86, 'geopolitics', 'high'),
        (r'tariff|sanction|trade', 84, 'trade_policy', 'medium'),
        (r'crypto|stablecoin|liquidity', 76, 'crypto_liquidity', 'medium'),
    ]
    for pattern, priority, family, impact in rules:
        if re.search(pattern, lower):
            return priority, family, impact
    return 60, 'headline', 'watch'


def _dedupe_texts(items: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for item in items:
        key = str(item).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(str(item))
    return out


def _build_ranked_event_bubble(events: list[dict], news_state: dict, extra_events: list[dict]) -> list[dict]:
    ranked = []
    seen_titles: set[str] = set()

    def add_item(title: str, family: str, when: str, priority: int, impact: str, countdown: str = '-', source: str = 'macro'):
        key = title.strip().lower()
        if not key or key in seen_titles:
            return
        seen_titles.add(key)
        ranked.append({
            'title': title,
            'family': family,
            'when': when,
            'priority': int(priority),
            'impact': impact,
            'countdown': countdown,
            'source': source,
        })

    for ev in events:
        title = str(ev.get('title', '')).strip()
        if not title:
            continue
        priority = int(ev.get('priority', 70))
        family = str(ev.get('family', 'macro'))
        when = str(ev.get('label', ev.get('event_dt', '')))
        countdown = _format_countdown(_parse_dt(ev.get('event_dt')))
        add_item(title, family, when, priority, 'high' if priority >= 85 else ('medium' if priority >= 72 else 'watch'), countdown, 'macro')

    for title in (news_state.get('top_headlines') or [])[:6]:
        priority, family, impact = _headline_priority(str(title))
        add_item(str(title), family, 'headline', priority, impact, '-', 'news')

    for ev in (extra_events or [])[:20]:
        title = str(ev.get('title', '')).strip()
        if not title:
            continue
        family = str(ev.get('family', 'event'))
        priority = int(ev.get('priority', 65))
        when = str(ev.get('label', ev.get('event_dt', 'event')))
        countdown = _format_countdown(_parse_dt(ev.get('event_dt')))
        add_item(title, family, when, priority, 'watch', countdown, 'event')

    ranked.sort(key=lambda x: (-x['priority'], x['countdown'], x['title'].lower()))
    return ranked[:12]
