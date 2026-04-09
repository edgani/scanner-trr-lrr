from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


MARKET_KEY_MAP = {
    'us': 'us',
    'ihsg': 'ihsg',
    'forex': 'fx',
    'fx': 'fx',
    'commodities': 'commodities',
    'crypto': 'crypto',
}

MACRO_ROUTE_BRANCH_KEY = {
    'us': 'US',
    'ihsg': 'IHSG',
    'forex': 'FX',
    'commodities': 'Commodities',
    'crypto': 'Crypto',
}


QUAD_MARKET_POLICY: dict[str, dict[str, dict[str, set[str]]]] = {
    'Q1': {
        'us': {
            'supportive': {'quality_growth', 'financials', 'defensives'},
            'next': {'energy', 'cyclical', 'small_beta'},
            'cut': {'precious'},
            'short': set(),
        },
        'ihsg': {
            'supportive': {'banks', 'cyclical', 'telco_defensive'},
            'next': {'metals_energy', 'energy_exporter'},
            'cut': set(),
            'short': set(),
        },
        'forex': {
            'supportive': {'carry_beta', 'commodity_fx'},
            'next': {'usd_major'},
            'cut': {'jpy_safe_haven', 'safe_haven_fx'},
            'short': set(),
        },
        'commodities': {
            'supportive': {'industrial', 'energy'},
            'next': {'precious'},
            'cut': set(),
            'short': set(),
        },
        'crypto': {
            'supportive': {'majors', 'l1l2', 'defi', 'infra'},
            'next': {'high_beta', 'meme_beta'},
            'cut': {'btc_quality'},
            'short': set(),
        },
    },
    'Q2': {
        'us': {
            'supportive': {'energy', 'cyclical', 'small_beta'},
            'next': {'financials', 'quality_growth'},
            'cut': {'defensives'},
            'short': set(),
        },
        'ihsg': {
            'supportive': {'energy_exporter', 'metals_energy', 'banks'},
            'next': {'cyclical'},
            'cut': {'telco_defensive'},
            'short': set(),
        },
        'forex': {
            'supportive': {'commodity_fx', 'carry_beta', 'em_fx'},
            'next': {'usd_major'},
            'cut': {'jpy_safe_haven', 'safe_haven_fx'},
            'short': set(),
        },
        'commodities': {
            'supportive': {'energy', 'industrial'},
            'next': {'precious'},
            'cut': set(),
            'short': set(),
        },
        'crypto': {
            'supportive': {'majors', 'l1l2', 'defi', 'infra', 'high_beta'},
            'next': {'meme_beta'},
            'cut': {'btc_quality'},
            'short': set(),
        },
    },
    'Q3': {
        'us': {
            'supportive': {'energy', 'defensives', 'quality_growth'},
            'next': {'financials'},
            'cut': {'small_beta', 'high_beta', 'consumer_cyc', 'semis_beta'},
            'short': {'small_beta', 'high_beta', 'consumer_cyc'},
        },
        'ihsg': {
            'supportive': {'banks', 'energy_exporter', 'metals_energy'},
            'next': {'telco_defensive'},
            'cut': {'cyclical'},
            'short': {'cyclical'},
        },
        'forex': {
            'supportive': {'usd_major', 'commodity_fx'},
            'next': {'jpy_safe_haven', 'safe_haven_fx'},
            'cut': {'carry_beta', 'em_fx'},
            'short': {'carry_beta', 'em_fx'},
        },
        'commodities': {
            'supportive': {'energy', 'precious'},
            'next': {'industrial'},
            'cut': set(),
            'short': set(),
        },
        'crypto': {
            'supportive': {'btc_quality', 'majors'},
            'next': {'infra', 'defi'},
            'cut': {'high_beta', 'meme_beta', 'micro_alt'},
            'short': {'high_beta', 'meme_beta'},
        },
    },
    'Q4': {
        'us': {
            'supportive': {'defensives', 'quality_growth', 'energy'},
            'next': {'financials'},
            'cut': {'small_beta', 'high_beta', 'consumer_cyc', 'semis_beta'},
            'short': {'small_beta', 'high_beta'},
        },
        'ihsg': {
            'supportive': {'banks', 'energy_exporter', 'telco_defensive'},
            'next': {'metals_energy'},
            'cut': {'cyclical'},
            'short': {'cyclical'},
        },
        'forex': {
            'supportive': {'usd_major', 'jpy_safe_haven', 'safe_haven_fx'},
            'next': {'commodity_fx'},
            'cut': {'carry_beta', 'em_fx'},
            'short': {'carry_beta', 'em_fx'},
        },
        'commodities': {
            'supportive': {'precious', 'energy'},
            'next': {'industrial'},
            'cut': set(),
            'short': set(),
        },
        'crypto': {
            'supportive': {'btc_quality', 'majors'},
            'next': {'infra'},
            'cut': {'high_beta', 'meme_beta', 'micro_alt', 'defi'},
            'short': {'high_beta', 'meme_beta', 'micro_alt'},
        },
    },
}


ROUTE_TO_BUCKETS: dict[str, dict[str, set[str]]] = {
    'TLT': {
        'us': {'defensives', 'quality_growth'},
        'ihsg': {'banks', 'telco_defensive'},
        'forex': {'usd_major', 'jpy_safe_haven', 'safe_haven_fx'},
        'commodities': {'precious'},
        'crypto': {'btc_quality', 'majors'},
    },
    'USD': {
        'us': {'defensives'},
        'ihsg': {'banks'},
        'forex': {'usd_major', 'jpy_safe_haven', 'safe_haven_fx'},
        'commodities': {'precious'},
        'crypto': {'btc_quality'},
    },
    'XAUUSD': {
        'us': {'defensives', 'energy'},
        'ihsg': {'energy_exporter', 'metals_energy'},
        'forex': {'safe_haven_fx'},
        'commodities': {'precious'},
        'crypto': {'btc_quality'},
    },
    'WTI': {
        'us': {'energy'},
        'ihsg': {'energy_exporter'},
        'forex': {'commodity_fx'},
        'commodities': {'energy'},
        'crypto': {'majors'},
    },
    'IHSG': {
        'ihsg': {'banks', 'energy_exporter', 'metals_energy'},
    },
    'EEM': {
        'ihsg': {'banks', 'cyclical'},
        'forex': {'em_fx', 'commodity_fx'},
    },
}


MARKET_LABEL_TO_BUCKETS: dict[str, dict[str, set[str]]] = {
    'us': {
        'Growth': {'quality_growth'},
        'Quality': {'quality_growth'},
        'Defensives': {'defensives'},
        'Energy': {'energy'},
        'Financials': {'financials'},
        'Small Caps': {'small_beta'},
        'Semis': {'semis_beta'},
        'Cyclicals': {'consumer_cyc', 'small_beta'},
    },
    'ihsg': {
        'Banks': {'banks'},
        'Coal/Energy': {'energy_exporter'},
        'Metals': {'metals_energy'},
        'Telco/Defensive': {'telco_defensive'},
        'Cyclicals': {'cyclical'},
    },
    'forex': {
        'Majors': {'usd_major'},
        'JPY Crosses': {'jpy_safe_haven'},
        'Core Crosses': {'safe_haven_fx', 'usd_major'},
        'Carry': {'carry_beta'},
        'EM FX': {'em_fx'},
    },
    'commodities': {
        'Precious': {'precious'},
        'Energy': {'energy'},
        'Industrial': {'industrial'},
    },
    'crypto': {
        'Majors': {'majors', 'btc_quality'},
        'L1/L2': {'l1l2'},
        'DeFi': {'defi'},
        'Infra': {'infra'},
        'Beta': {'high_beta', 'meme_beta'},
    },
}


@dataclass
class MarketBrain:
    market: str
    current_route: str
    next_route: str
    invalidator_route: str
    execution_mode: str
    execution_bias: str
    shock_state: str
    health_state: str
    crash_state: str
    supportive_buckets: set[str]
    next_buckets: set[str]
    cut_buckets: set[str]
    short_buckets: set[str]
    safe_harbor_buckets: set[str]
    beneficiary_buckets: set[str]
    no_chase_default: bool
    short_bounces_only: bool
    no_trade: bool
    route_confirmations: list[str]
    route_invalidators: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            'market': self.market,
            'current_route': self.current_route,
            'next_route': self.next_route,
            'invalidator_route': self.invalidator_route,
            'execution_mode': self.execution_mode,
            'execution_bias': self.execution_bias,
            'shock_state': self.shock_state,
            'health_state': self.health_state,
            'crash_state': self.crash_state,
            'supportive_buckets': sorted(self.supportive_buckets),
            'next_buckets': sorted(self.next_buckets),
            'cut_buckets': sorted(self.cut_buckets),
            'short_buckets': sorted(self.short_buckets),
            'safe_harbor_buckets': sorted(self.safe_harbor_buckets),
            'beneficiary_buckets': sorted(self.beneficiary_buckets),
            'no_chase_default': self.no_chase_default,
            'short_bounces_only': self.short_bounces_only,
            'no_trade': self.no_trade,
            'route_confirmations': self.route_confirmations,
            'route_invalidators': self.route_invalidators,
        }


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def _market_alias(market: str) -> str:
    market = str(market).lower().strip()
    if market == 'fx':
        return 'forex'
    return market


def _route_overlay(route_name: str, market: str) -> set[str]:
    route_name = str(route_name or '').strip()
    return set(ROUTE_TO_BUCKETS.get(route_name, {}).get(_market_alias(market), set()))


def _market_label_overlay(labels: list[str] | None, market: str) -> set[str]:
    mapping = MARKET_LABEL_TO_BUCKETS.get(_market_alias(market), {})
    out: set[str] = set()
    for label in labels or []:
        out |= set(mapping.get(str(label).strip(), set()))
    return out


def _candidate_macro_roots() -> list[Path]:
    env_root = os.getenv('SCANNER_MACRO_ROOT')
    out: list[Path] = []
    if env_root:
        out.append(Path(env_root))
    parent = ROOT.parent
    out.extend([
        parent / 'v33_final',
        parent / 'macroregime_v33',
        parent / 'MacroRegime_Pro_v33_final_mentok',
    ])
    for p in parent.iterdir():
        if p.is_dir() and (p / '.cache' / 'latest_snapshot.json').exists():
            out.append(p)
    dedup: list[Path] = []
    seen: set[str] = set()
    for p in out:
        rp = str(p.resolve()) if p.exists() else str(p)
        if rp not in seen:
            dedup.append(p)
            seen.add(rp)
    return dedup


def resolve_macro_root() -> Path:
    for p in _candidate_macro_roots():
        if (p / '.cache' / 'latest_snapshot.json').exists():
            return p
    return ROOT.parent / 'v33_final'


def resolve_macro_file() -> Path:
    env_file = os.getenv('SCANNER_MACRO_FILE')
    if env_file:
        p = Path(env_file)
        if p.is_dir():
            return p / '.cache' / 'latest_snapshot.json'
        return p
    return resolve_macro_root() / '.cache' / 'latest_snapshot.json'


def scanner_brain_file() -> Path:
    env_out = os.getenv('SCANNER_BRAIN_FILE')
    if env_out:
        return Path(env_out)
    return ROOT / 'data' / 'macro' / 'scanner_brain.json'


def _core_and_sections(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if 'shared_core' in raw:
        core = raw.get('shared_core', {}) or {}
        sections = {k: raw.get(k, {}) or {} for k in ['us', 'ihsg', 'fx', 'commodities', 'crypto']}
        return core, sections, raw
    sections = {k: raw.get(k, {}) or {} for k in ['us', 'ihsg', 'fx', 'commodities', 'crypto']}
    return raw, sections, raw


def normalize_raw_macro(raw: dict[str, Any]) -> dict[str, Any]:
    if not raw:
        return {}

    core, sections, snapshot = _core_and_sections(raw)
    meta = snapshot.get('meta', {}) if isinstance(snapshot.get('meta'), dict) else {}
    status = core.get('status_ribbon', {}) or {}
    execution = core.get('execution_mode', {}) or {}
    next_path = core.get('next_path', {}) or {}
    risk = core.get('risk_summary', {}) or {}
    master_routes = snapshot.get('master_routes', {}) or {}

    current_quad = str(status.get('current_quad') or 'unknown')
    structural_quad = str(status.get('structural_quad') or 'unknown')
    monthly_quad = str(status.get('monthly_quad') or 'unknown')
    next_quad = str(next_path.get('next_structural_quad') or next_path.get('next_monthly_quad') or 'unknown')

    health_verdict = str((core.get('health', {}) or {}).get('verdict') or status.get('health') or 'unknown')
    shock_state = str((core.get('shock', {}) or {}).get('state') or 'unknown')
    crash_state = str(risk.get('crash_state') or status.get('crash') or 'unknown')
    risk_off_state = str(risk.get('risk_off_state') or status.get('risk_off') or 'unknown')
    safe_harbor = str(core.get('safe_harbor') or status.get('safe_harbor') or '')
    best_beneficiary = str(core.get('best_beneficiary') or status.get('best_beneficiary') or '')

    current_route = str(
        master_routes.get('dominant_summary')
        or core.get('next_macro_summary')
        or next_path.get('continuation_path')
        or status.get('resolved_language')
        or status.get('operating_regime')
        or ''
    )
    next_route = str(
        next_path.get('structural_flip_path')
        or next_path.get('monthly_fade_path')
        or next_path.get('next_resolved_regime')
        or ''
    )
    alt_route = ''
    alt_routes = master_routes.get('alternate_routes') or []
    if alt_routes and isinstance(alt_routes, list):
        alt_route = str((alt_routes[0] or {}).get('summary') or (alt_routes[0] or {}).get('name') or '')
    invalidator_route = ' | '.join((master_routes.get('global_invalidators') or next_path.get('invalidators') or [])[:3])

    global_flags = execution.get('flags', {}) if isinstance(execution.get('flags'), dict) else {}
    market_brains: dict[str, dict[str, Any]] = {}

    for scanner_market in ['us', 'ihsg', 'forex', 'commodities', 'crypto']:
        macro_market = MARKET_KEY_MAP[scanner_market]
        section = sections.get(macro_market, {}) or {}
        route_branch = section.get('route_branch', {}) or (master_routes.get('market_branches', {}) or {}).get(MACRO_ROUTE_BRANCH_KEY[scanner_market], {}) or {}
        section_execution = section.get('execution', {}) or {}
        market_next_route = str((section.get('next_path', {}) or {}).get('summary') or next_path.get('market_routes', {}).get(macro_market) or next_route)
        market_invalidators = route_branch.get('market_invalidators') or next_path.get('invalidators') or []
        market_confirmations = route_branch.get('market_confirmations') or master_routes.get('global_confirmations') or []

        base_policy = QUAD_MARKET_POLICY.get(current_quad, QUAD_MARKET_POLICY['Q4']).get(scanner_market, {})
        supportive = set(base_policy.get('supportive', set()))
        next_buckets = set(base_policy.get('next', set()))
        cut_buckets = set(base_policy.get('cut', set()))
        short_buckets = set(base_policy.get('short', set()))

        winners = route_branch.get('winners') if isinstance(route_branch.get('winners'), list) else []
        losers = route_branch.get('losers') if isinstance(route_branch.get('losers'), list) else []
        winner_overlay = _market_label_overlay(winners, scanner_market)
        loser_overlay = _market_label_overlay(losers, scanner_market)
        if set(map(str, winners)) == set(map(str, losers)) or loser_overlay == winner_overlay:
            loser_overlay = set()
        supportive |= winner_overlay
        next_buckets |= _route_overlay(best_beneficiary, scanner_market)
        supportive |= _route_overlay(safe_harbor, scanner_market)
        supportive |= _route_overlay(best_beneficiary, scanner_market)
        # Treat route losers only as short/cut overlays when risk backdrop is not benign.
        if health_verdict.lower() in {'fragile', 'weak'} or crash_state.lower() in {'watch', 'warning', 'elevated', 'high'}:
            cut_buckets |= loser_overlay
            short_buckets |= loser_overlay
            cut_buckets |= {'high_beta', 'small_beta', 'meme_beta', 'micro_alt', 'carry_beta'}
            short_buckets |= {'high_beta', 'small_beta', 'meme_beta'}
        if shock_state.lower() not in {'normal', 'calm'}:
            if scanner_market == 'commodities':
                supportive |= {'precious', 'energy'}
            if scanner_market == 'forex':
                cut_buckets |= {'carry_beta', 'em_fx'}
                short_buckets |= {'carry_beta', 'em_fx'}
        if risk_off_state.lower() in {'watch', 'elevated', 'high'} and scanner_market == 'crypto':
            cut_buckets |= {'high_beta', 'meme_beta', 'micro_alt'}
            short_buckets |= {'high_beta', 'meme_beta'}

        flags = dict(global_flags)
        if isinstance(section_execution.get('flags'), dict):
            flags.update(section_execution.get('flags', {}))

        execution_mode = str(section_execution.get('mode') or execution.get('execute_mode') or execution.get('mode') or 'balanced')
        execution_bias = str(section_execution.get('bias') or 'neutral')
        route_summary = str(route_branch.get('summary') or '').strip()
        current_market_route = str((route_summary if route_summary and route_summary != '-' else '') or route_branch.get('route_interpretation') or current_route)

        market_brain = MarketBrain(
            market=scanner_market,
            current_route=current_market_route,
            next_route=market_next_route,
            invalidator_route=' | '.join(market_invalidators[:3]),
            execution_mode=execution_mode,
            execution_bias=execution_bias,
            shock_state=shock_state,
            health_state=health_verdict,
            crash_state=crash_state,
            supportive_buckets=supportive,
            next_buckets=next_buckets,
            cut_buckets=cut_buckets,
            short_buckets=short_buckets,
            safe_harbor_buckets=_route_overlay(safe_harbor, scanner_market),
            beneficiary_buckets=_route_overlay(best_beneficiary, scanner_market),
            no_chase_default=not bool(flags.get('can_chase', False)),
            short_bounces_only=bool(flags.get('short_bounces_only', False)),
            no_trade=bool(flags.get('no_trade', False)),
            route_confirmations=list(market_confirmations[:5]),
            route_invalidators=list(market_invalidators[:5]),
        )
        market_brains[scanner_market] = market_brain.to_dict()

    return {
        'generated_at': meta.get('generated_at') or snapshot.get('generated_at'),
        'source_macro_root': str(resolve_macro_root()),
        'source_snapshot_file': str(resolve_macro_file()),
        'source': 'MacroRegime v33',
        'structural_quad': structural_quad,
        'monthly_quad': monthly_quad,
        'current_quad': current_quad,
        'next_quad': next_quad,
        'current_route': current_route,
        'next_route': next_route,
        'alt_route': alt_route,
        'invalidator_route': invalidator_route,
        'execution_mode': {
            'mode': str(execution.get('mode') or 'balanced'),
            'label': str(execution.get('execute_mode') or execution.get('mode') or 'balanced'),
            'score': execution.get('score'),
            'size_multiplier': execution.get('size_multiplier'),
            'flags': global_flags,
            'notes': execution.get('notes', []),
        },
        'shock_state': shock_state,
        'market_health': health_verdict,
        'risk_off_state': risk_off_state,
        'crash_state': crash_state,
        'safe_harbor': safe_harbor,
        'best_beneficiary': best_beneficiary,
        'market_brains': market_brains,
    }


def load_brain() -> dict[str, Any]:
    payload = _load_json(scanner_brain_file())
    if payload:
        return payload
    raw = _load_json(resolve_macro_file())
    return normalize_raw_macro(raw)


def export_brain(source_file: Path | None = None, target_file: Path | None = None) -> dict[str, Any]:
    source_file = source_file or resolve_macro_file()
    if source_file.is_dir():
        source_file = source_file / '.cache' / 'latest_snapshot.json'
    target_file = target_file or scanner_brain_file()
    raw = _load_json(source_file)
    payload = normalize_raw_macro(raw)
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return payload


def current_quad(brain: dict[str, Any]) -> str:
    return str(brain.get('current_quad') or 'unknown')


def next_route(brain: dict[str, Any]) -> dict[str, Any]:
    return {'market_routes': {('fx' if k == 'forex' else k): v.get('next_route', '') for k, v in (brain.get('market_brains', {}) or {}).items()}}


def execution_mode(brain: dict[str, Any]) -> str:
    mode = brain.get('execution_mode', {})
    if isinstance(mode, dict):
        return str(mode.get('label') or mode.get('mode') or 'balanced')
    return str(mode or 'balanced')


def crash_state(brain: dict[str, Any]) -> str:
    return str(brain.get('crash_state') or 'unknown')


def market_policy(brain: dict[str, Any], market: str) -> dict[str, Any]:
    market = _market_alias(market)
    out = ((brain.get('market_brains', {}) or {}).get(market) or {}).copy()
    for key in ['supportive_buckets', 'next_buckets', 'cut_buckets', 'short_buckets', 'safe_harbor_buckets', 'beneficiary_buckets']:
        out[key] = set(out.get(key, []) or [])
    return out


bucket_policy = market_policy
