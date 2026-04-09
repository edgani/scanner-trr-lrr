from __future__ import annotations

from datetime import datetime
from typing import Any


from config.settings import DEFAULT_PRICE_PERIOD, LIVE_RUNTIME_MODE, SNAPSHOT_SCHEMA
from config.universes import FULL_UNIVERSE
from config.asset_buckets import US_BUCKETS, IHSG_BUCKETS, FX_BUCKETS, COMMODITY_BUCKETS, CRYPTO_BUCKETS
from config.universe_registry import US_BACKEND_UNIVERSE, IHSG_BACKEND_UNIVERSE, FX_BACKEND_UNIVERSE, COMMODITIES_BACKEND_UNIVERSE, CRYPTO_BACKEND_UNIVERSE, build_coverage_report
from data.loaders import load_all_data
from data.snapshot_store import load_snapshot, save_snapshot, load_snapshot_manifest
from data.history_store import history_coverage
from features.macro_features import build_macro_features
from features.market_features import build_market_features
from features.breadth_features import build_breadth_features
from features.vol_credit_features import build_vol_credit_features
from features.plumbing_features import build_plumbing_features
from features.scenario_features import build_scenario_features
from features.positioning_features import build_positioning_features
from features.derivatives_vol_features import build_derivatives_vol_features
from features.us_equity_features import build_us_equity_features
from features.ihsg_native_features import build_ihsg_native_features
from features.fx_native_features import build_fx_native_features
from features.commodity_native_features import build_commodity_native_features
from features.crypto_native_features import build_crypto_native_features
from engines.shared_core_engine import build_shared_core
from engines.macro_impact_board_engine import build_macro_impact_sections
from engines.transmission_engine import build_transmission_sections
from engines.checklist_engine import build_asset_checklists
from engines.us_equity_engine import run_us_equity_engine
from engines.ihsg_native_engine import run_ihsg_native_engine
from engines.fx_native_engine import run_fx_native_engine
from engines.commodity_native_engine import run_commodity_native_engine
from engines.crypto_native_engine import run_crypto_native_engine
from orchestration.route_layers import (
    build_master_routes,
    build_master_opportunities,
    build_position_lifecycle,
    build_home_summary,
    build_scenario_lab,
    attach_market_views,
)


def _top_list(items, n=3):
    out = []
    for x in (items or [])[:n]:
        sx = str(x).strip()
        if sx and sx not in out:
            out.append(sx)
    return out


def _top_tickers_from_section(section: dict, n: int = 3) -> list[str]:
    out = []
    sw = section.get('strong_weak', {}) or {}
    for bucket in ('strong', 'weak'):
        for item in (sw.get(bucket, []) or [])[:n]:
            sx = str(item).strip()
            if sx and sx not in out:
                out.append(sx)
            if len(out) >= n:
                return out
    return out


def _extract_name(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get('ticker') or item.get('name') or item.get('symbol') or '').strip()
    return str(item).strip()


def _names_from_rows(rows: list[dict] | None, side: str | None = None, n: int = 6) -> list[str]:
    out: list[str] = []
    for row in rows or []:
        if side and str(row.get('side', '')).lower() != side.lower():
            continue
        sx = _extract_name(row)
        if sx and sx not in out:
            out.append(sx)
        if len(out) >= n:
            break
    return out


def _name_list_from_section(section: dict, kind: str, n: int = 6) -> list[str]:
    out: list[str] = []
    sw = section.get('strong_weak', {}) or {}
    if not isinstance(sw, dict):
        sw = {}

    pref = [
        f'{kind}_names',
        f'{kind}_pairs',
        f'{kind}_tokens',
        f'{kind}_currencies',
        f'{kind}_symbols',
        f'{kind}_sectors',
        f'{kind}_families',
        kind,
    ]
    used = set()
    ordered_keys = []
    for key in pref:
        if key in sw and key not in used:
            ordered_keys.append(key)
            used.add(key)
    for key in sw.keys():
        if key.startswith(f'{kind}_') and key not in used:
            ordered_keys.append(key)
            used.add(key)

    for key in ordered_keys:
        for item in sw.get(key, []) or []:
            sx = _extract_name(item)
            if sx and sx not in out:
                out.append(sx)
            if len(out) >= n:
                return out
    return out


def _pick_slice(items, start: int, n: int, fallback=None) -> list[str]:
    clean = []
    for x in items or []:
        sx = str(x).strip()
        if sx and sx not in clean:
            clean.append(sx)
    picked = clean[start:start+n]
    if picked:
        return picked
    fb = []
    for x in fallback or []:
        sx = str(x).strip()
        if sx and sx not in fb:
            fb.append(sx)
        if len(fb) >= n:
            break
    return fb



def _coverage_reports() -> dict:
    return {
        "us": build_coverage_report(US_BUCKETS, US_BACKEND_UNIVERSE),
        "ihsg": build_coverage_report(IHSG_BUCKETS, IHSG_BACKEND_UNIVERSE),
        "fx": build_coverage_report(FX_BUCKETS, FX_BACKEND_UNIVERSE),
        "commodities": build_coverage_report(COMMODITY_BUCKETS, COMMODITIES_BACKEND_UNIVERSE),
        "crypto": build_coverage_report(CRYPTO_BUCKETS, CRYPTO_BACKEND_UNIVERSE),
    }


def _build_market_catalyst(market: str, section: dict, shared_core: dict) -> dict:
    setups = section.get("setups_now", []) or []
    radar = section.get("forward_radar", []) or []
    long_live = _names_from_rows(setups, "long", 4)
    short_live = _names_from_rows(setups, "short", 3)
    watch = _names_from_rows(radar, "long", 4)
    risk = shared_core.get("risk_summary", {}) or {}
    breadth = shared_core.get("breadth_snapshot", {}) or {}
    news_state = str(shared_core.get("news_state", {}).get("display_state", shared_core.get("news_state", {}).get("state", "Quiet")))
    if market == "ihsg":
        beneficiaries = [x for x in long_live if x in {"BBCA", "BBRI", "BMRI", "TLKM", "ASII", "BBNI"}] or [x.replace('.JK','') for x in ["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK", "BBNI.JK"][:4]]
        return {
            "title": "EM reweight / Korea reclassification watch",
            "state": "active watch" if float(shared_core.get("em_rotation", {}).get("resolved_score", shared_core.get("em_rotation", {}).get("score", 0.4)) or 0.4) >= 0.50 else "background",
            "why": "Kalau EM flow/reweight narrative jadi real, beneficiary awal biasanya big-cap liquid Indonesia proxies.",
            "beneficiaries": beneficiaries[:4],
            "watch": watch[:4],
            "trigger": "foreign flow stabil + banks / big caps lead + breadth tidak sempit",
            "invalidator": "DXY & USD/IDR naik lagi, risk-off global, breadth IHSG rusak",
        }
    if market == "us":
        return {
            "title": "Rates / breadth / concentration route",
            "state": "active" if float(breadth.get("breadth_score", 0.5) or 0.5) >= 0.52 else "watch",
            "why": "US winners paling valid kalau breadth ikut membaik, bukan cuma nama besar tertentu.",
            "beneficiaries": long_live[:4],
            "watch": watch[:4],
            "trigger": "equal-weight & small caps ikut confirm / yields tidak spike",
            "invalidator": "breadth sempit lagi / yield spike / crash meter naik",
        }
    if market == "fx":
        return {
            "title": "Rate differential / USD route",
            "state": "active",
            "why": "FX paling sering berubah arah kalau rate repricing, growth surprise, dan USD liquidity route berubah.",
            "beneficiaries": long_live[:4],
            "watch": watch[:4],
            "trigger": "macro surprise + rate repricing + intervention risk rendah",
            "invalidator": "intervention / policy surprise berlawanan",
        }
    if market == "commodities":
        return {
            "title": "Petrodollar / hard-assets route",
            "state": "active" if float(shared_core.get("petrodollar", {}).get("score", 0.0) or 0.0) >= 0.50 else "watch",
            "why": "Komoditas perlu lihat apakah oil / USD / yields mendorong hard assets atau malah menekan cyclicals.",
            "beneficiaries": long_live[:4],
            "watch": watch[:4],
            "trigger": "curve tightens / oil route confirms / USD tidak terlalu menekan",
            "invalidator": "USD spike / demand scare / inventory pressure",
        }
    return {
        "title": "Liquidity / breadth / trust route",
        "state": "active" if news_state not in {"Policy pressure", "War / oil"} else "watch",
        "why": "Crypto terbaik saat breadth melebar dari majors ke beta tanpa fragility berlebihan.",
        "beneficiaries": long_live[:4],
        "watch": watch[:4],
        "trigger": "majors confirm + breadth melebar + flow membaik",
        "invalidator": "funding panas, exchange inflow naik, risk-off makro",
    }


def _market_branch(section: dict, market_key: str) -> dict:
    tx = section.get('transmission', {}) or {}
    hub = section.get('market_hub', {}) or {}
    summary = section.get('macro_vs_market', {}).get('resolved_language', hub.get('resolved_language', '-'))
    strong = _name_list_from_section(section, 'strong', 10)
    weak = _name_list_from_section(section, 'weak', 8)
    watch = _name_list_from_section(section, 'watch', 8)

    live_long = _names_from_rows(section.get('setups_now', []), 'long', 8)
    live_short = _names_from_rows(section.get('setups_now', []), 'short', 8)
    radar_long = _names_from_rows(section.get('forward_radar', []), 'long', 8)
    radar_short = _names_from_rows(section.get('forward_radar', []), 'short', 8)
    execution_focus = [str(x).strip() for x in (hub.get('execution_focus', []) or []) if str(x).strip()]

    structural_tickers = _pick_slice(live_long or execution_focus or strong, 0, 3, fallback=strong)
    monthly_tickers = _pick_slice(radar_long or strong, 0, 3, fallback=structural_tickers)
    resolved_tickers = _pick_slice(live_long or strong, 0, 3, fallback=structural_tickers)
    receiver_tickers = _pick_slice(execution_focus or strong, 0, 3, fallback=resolved_tickers)
    next_tickers = _pick_slice(radar_long or watch or strong, 0, 3, fallback=_pick_slice(strong, 3, 3, fallback=resolved_tickers))
    risk_tickers = _pick_slice(live_short or radar_short or weak, 0, 3, fallback=_top_tickers_from_section(section, 3))

    next_route = section.get('next_path', {}).get('market_routes', {}).get(market_key, section.get('next_path', {}).get('next_resolved_regime', '-'))
    invalidators = (section.get('next_path', {}) or {}).get('invalidators', [])[:3]
    return {
        'market': market_key,
        'summary': summary,
        'structural_role': tx.get('structural_route', '-'),
        'structural_summary': tx.get('structural_paths', ['-'])[0],
        'structural_tickers': structural_tickers,
        'monthly_role': tx.get('monthly_trigger', '-'),
        'monthly_summary': tx.get('monthly_paths', ['-'])[0],
        'monthly_tickers': monthly_tickers,
        'resolved_role': tx.get('dominant', hub.get('resolved_language', '-')),
        'resolved_summary': tx.get('resolved_paths', ['-'])[0],
        'resolved_tickers': resolved_tickers,
        'receiver_label': ', '.join(receiver_tickers[:2]) or '-',
        'receiver_summary': 'top live receivers in this market branch',
        'receiver_tickers': receiver_tickers,
        'next_route': next_route,
        'next_summary': section.get('next_path', {}).get('continuation_path', '-'),
        'next_tickers': next_tickers,
        'top_tickers': resolved_tickers,
        'risk_tickers': risk_tickers,
        'current_stage': 'resolved',
        'current_stage_label': hub.get('resolved_language', tx.get('dominant', '-')),
        'active_path': f"{tx.get('structural_quad', '-')} → {tx.get('monthly_quad', '-')} → {hub.get('resolved_language', tx.get('dominant', '-'))}",
        'invalidators': invalidators,
        'invalidator_summary': 'watch breadth / USD / credit failure',
        'edges': {
            'struct_to_month': tx.get('structural_route', 'sets backdrop'),
            'month_to_resolved': tx.get('monthly_trigger', 'narrows route'),
            'resolved_to_receivers': tx.get('dominant', 'hands off to receivers'),
            'receivers_to_next': next_route,
        },
    }


def _build_master_correlated_rotation_graph(shared_core: dict, sections: dict, transmissions: dict) -> dict:
    regime = shared_core.get('regime_stack', {}) or {}
    struct = regime.get('structural', {}) or {}
    month = regime.get('monthly', {}) or {}
    resolved = regime.get('resolved', {}) or {}
    next_path = shared_core.get('next_path', {}) or {}
    rotation = shared_core.get('rotation', {}) or {}
    breadth = shared_core.get('breadth_snapshot', {}) or {}
    scenario_fam = shared_core.get('scenario_family', []) or []
    petrodollar = shared_core.get('petrodollar', {}) or {}
    em_rotation = shared_core.get('em_rotation', {}) or {}

    current_stage = 'resolved'
    if float(next_path.get('flip_hazard', 0.0) or 0.0) >= 0.68:
        current_stage = 'next'
    elif breadth.get('breadth_state') in {'narrow / fragile', 'fragile', 'mixed / watch'} or breadth.get('breadth_trend') in {'fragile', 'deteriorating'}:
        current_stage = 'spillover'
    elif resolved.get('dominant_horizon') == 'structural':
        current_stage = 'structural'
    elif resolved.get('dominant_horizon') == 'monthly':
        current_stage = 'monthly'

    branches = {k: _market_branch(v, k) for k, v in sections.items()}

    branch_values = list(branches.values())
    struct_tickers = _top_list([x for b in branch_values for x in (b.get('structural_tickers') or [])], 5)
    month_tickers = _top_list([x for b in branch_values for x in (b.get('monthly_tickers') or [])], 5)
    resolved_tickers = _top_list([x for b in branch_values for x in (b.get('resolved_tickers') or [])], 5)
    next_tickers = _top_list([x for b in branch_values for x in (b.get('next_tickers') or [])], 5) or _top_list([x.get('quad', '-') for x in (next_path.get('structural_candidates', []) or [])], 3)
    danger_ticks = _top_list([x for b in branch_values for x in (b.get('risk_tickers') or [])], 5) or _top_list(rotation.get('resolved_rotation', {}).get('laggards', []), 3) or _top_list(rotation.get('next_rotation', {}).get('laggards', []), 3)

    return {
        'current_stage': current_stage,
        'you_are_here': resolved.get('resolved_language', resolved.get('operating_regime', '-')),
        'active_path': f"{struct.get('quad', '-')} → {month.get('quad', '-')} → {resolved.get('resolved_language', resolved.get('operating_regime', '-'))}",
        'next_branch_watch': next_path.get('next_resolved_regime', '-'),
        'structural': {
            'label': struct.get('quad', '-'),
            'summary': rotation.get('structural_rotation', {}).get('summary', '-'),
            'tickers': struct_tickers,
            'confidence': struct.get('confidence', 0.0),
        },
        'monthly': {
            'label': month.get('quad', '-'),
            'summary': rotation.get('monthly_rotation', {}).get('summary', '-'),
            'tickers': month_tickers,
            'confidence': month.get('confidence', 0.0),
        },
        'resolved': {
            'label': resolved.get('resolved_language', resolved.get('operating_regime', '-')),
            'summary': rotation.get('resolved_rotation', {}).get('summary', '-'),
            'tickers': resolved_tickers,
            'confidence_band': resolved.get('confidence_band', 'low'),
        },
        'spillover': {
            'label': 'Receivers / spillover',
            'summary': 'Receiver markets pick up the route differently: US style/cyclicals, EM/IHSG, FX carry/funding, commodities, and crypto beta.',
            'tickers': _top_list(['SPY', '^JKSE', 'DXY', 'WTI', 'BTC-USD'], 5),
        },
        'next': {
            'label': next_path.get('next_resolved_regime', '-'),
            'summary': next_path.get('continuation_path', '-'),
            'tickers': next_tickers,
            'invalidators': next_path.get('invalidators', [])[:3],
        },
        'danger': {
            'label': 'Invalidator route',
            'summary': '; '.join((next_path.get('invalidators', []) or [])[:3]) or 'Watch breadth / USD / credit breakdown path',
            'tickers': danger_ticks,
        },
        'branches': branches,
        'petrodollar': {
            'state': petrodollar.get('state', 'normal'),
            'summary': petrodollar.get('next_route', 'Oil → shipping/tankers → importer pain → FX/EM'),
            'score': petrodollar.get('score', 0.0),
            'tickers': ['WTI', 'TNK', 'DXY', 'USDIDR=X'],
        },
        'em_rotation': {
            'state': em_rotation.get('resolved_state', em_rotation.get('state', '-')),
            'summary': em_rotation.get('next_route', 'EM exporters vs importers'),
            'tickers': ['^JKSE', 'USDIDR=X', 'ADRO', 'BBCA'],
        },
        'scenario_branches': scenario_fam[:4],
        'edge_labels': {
            'struct_to_month': 'backbone sets first receivers / family hierarchy',
            'month_to_resolved': 'monthly pulse broadens or narrows the lane',
            'resolved_to_spill': 'execution route hands off to market-specific receivers',
            'spill_to_next': 'breadth / credit / USD decide if the route broadens',
            'next_to_risk': 'fails if breadth / USD / credit invalidators hit',
        },
    }

def build_snapshot(
    force_refresh: bool = False,
    prefer_saved: bool = True,
    compact_mode: bool = True,
    **kwargs: Any,
) -> dict:
    """Build the shared app snapshot.

    Extra kwargs are accepted on purpose so older/newer app.py callers do not
    crash with a TypeError when the parameter surface changes.
    """
    # Backward/forward-compat aliases.
    if "refresh" in kwargs:
        force_refresh = bool(kwargs["refresh"])
    if "load_saved" in kwargs:
        prefer_saved = bool(kwargs["load_saved"])
    if "compact" in kwargs:
        compact_mode = bool(kwargs["compact"])

    if prefer_saved and not force_refresh:
        cached = load_snapshot()
        if isinstance(cached, dict) and cached.get("meta", {}).get("schema") == SNAPSHOT_SCHEMA:
            return cached

    raw = load_all_data(FULL_UNIVERSE, period=DEFAULT_PRICE_PERIOD, force_refresh=force_refresh, prefer_local_history=True)

    macro = build_macro_features(raw["fred"], raw["prices"], raw.get("loader_meta", {}))
    market = build_market_features(raw["prices"])
    breadth = build_breadth_features(market)
    vol_credit = build_vol_credit_features(market)
    plumbing = build_plumbing_features(macro, market)
    scenario = build_scenario_features(macro, market, plumbing)
    positioning = build_positioning_features(market)
    derivatives = build_derivatives_vol_features(raw["prices"], market)

    shared_features = {
        "macro": macro,
        "market": market,
        "breadth": breadth,
        "vol_credit": vol_credit,
        "plumbing": plumbing,
        "scenario": scenario,
        "positioning": positioning,
        "derivatives": derivatives,
    }

    shared_core = build_shared_core(shared_features, raw)

    native_features = {
        "us": build_us_equity_features(raw, shared_core),
        "ihsg": build_ihsg_native_features(raw, shared_core),
        "fx": build_fx_native_features(raw, shared_core),
        "commodities": build_commodity_native_features(raw, shared_core),
        "crypto": build_crypto_native_features(raw, shared_core),
    }

    asset_checklists = build_asset_checklists(shared_core, native_features)
    shared_core["asset_checklists"] = asset_checklists

    transmissions = build_transmission_sections(shared_core=shared_core, native_features=native_features)
    macro_boards = build_macro_impact_sections(shared_core=shared_core, native_features=native_features)

    us = run_us_equity_engine(raw, shared_core, native_features["us"], macro_boards["us"], transmissions["us"])
    ihsg = run_ihsg_native_engine(raw, shared_core, native_features["ihsg"], macro_boards["ihsg"], transmissions["ihsg"])
    fx = run_fx_native_engine(raw, shared_core, native_features["fx"], macro_boards["fx"], transmissions["fx"])
    commodities = run_commodity_native_engine(raw, shared_core, native_features["commodities"], macro_boards["commodities"], transmissions["commodities"])
    crypto = run_crypto_native_engine(raw, shared_core, native_features["crypto"], macro_boards["crypto"], transmissions["crypto"])

    coverage_reports = _coverage_reports()
    catalysts = {
        'us': _build_market_catalyst('us', us, shared_core),
        'ihsg': _build_market_catalyst('ihsg', ihsg, shared_core),
        'fx': _build_market_catalyst('fx', fx, shared_core),
        'commodities': _build_market_catalyst('commodities', commodities, shared_core),
        'crypto': _build_market_catalyst('crypto', crypto, shared_core),
    }

    for _name, _sec in {'us': us, 'ihsg': ihsg, 'fx': fx, 'commodities': commodities, 'crypto': crypto}.items():
        _sec['next_path'] = shared_core.get('next_path', {})
        _sec['flow_stack'] = shared_core.get('flow_stack', {})
        _sec['catalyst_overlay'] = catalysts.get(_name, {})
        _sec.setdefault('market_hub', {})['coverage_report'] = coverage_reports.get(_name, {})
        _sec['market_hub']['unbucketed_symbols_head'] = coverage_reports.get(_name, {}).get('unbucketed_symbols', [])[:8]

    market_cards = {
        "us": us["macro_vs_market"],
        "ihsg": ihsg["macro_vs_market"],
        "fx": fx["macro_vs_market"],
        "commodities": commodities["macro_vs_market"],
        "crypto": crypto["macro_vs_market"],
    }

    sections = {'us': us, 'ihsg': ihsg, 'fx': fx, 'commodities': commodities, 'crypto': crypto}
    master_graph = _build_master_correlated_rotation_graph(shared_core, sections, transmissions)
    prior_snapshot = load_snapshot()
    generated_at = datetime.utcnow().isoformat()
    master_routes = build_master_routes(shared_core, sections, master_graph, as_of=generated_at)
    master_opportunities = build_master_opportunities(sections, master_routes, as_of=generated_at, prior_snapshot=prior_snapshot)
    position_lifecycle = build_position_lifecycle(master_opportunities, master_routes, as_of=generated_at, prior_snapshot=prior_snapshot)
    home_summary = build_home_summary(master_routes, master_opportunities, position_lifecycle, shared_core)
    scenario_lab = build_scenario_lab(shared_core, master_routes)
    attach_market_views(sections, master_routes, master_opportunities)

    dashboard = {
        "macro_impact_global": shared_core["macro_impact_global"],
        "top_drivers": shared_core["top_drivers"],
        "top_risks": shared_core["top_risks"],
        "event_bubble": shared_core["event_bubble"],
        "next_macro": shared_core.get("next_macro", []),
        "next_macro_summary": shared_core.get("next_macro_summary", {}),
        "market_cards": market_cards,
        "global_checklist": shared_core["global_checklist"],
        "status_ribbon": shared_core["status_ribbon"],
        "risk_range": shared_core.get("risk_range", {}),
        "setup_preview": _preview({"US": us, "IHSG": ihsg, "FX": fx, "Commodities": commodities, "Crypto": crypto}, "setups_now"),
        "strongest_markets": _strongest_markets(market_cards),
        "next_path": shared_core.get("next_path", {}),
        "resolved_rotation": shared_core.get("rotation", {}).get("resolved_rotation", {}),
        "next_rotation": shared_core.get("rotation", {}).get("next_rotation", {}),
        "breadth_snapshot": shared_core.get("breadth_snapshot", {}),
        "master_graph": master_graph,
        "catalyst_overlays": catalysts,
        "coverage_reports": coverage_reports,
        "quick_transmission": {
            "rates_to_usd": "rates -> USD -> equities",
            "dxy_to_em": "DXY -> EM/IHSG",
            "oil_to_inflation": "oil -> inflation -> yields",
            "liquidity_to_crypto": "liquidity -> crypto beta",
            "gold_to_miners": "gold -> miners / real-yield-sensitive names",
        },
    }

    history_meta = history_coverage(FULL_UNIVERSE)
    prior_manifest = load_snapshot_manifest() or {}

    snapshot = {
        "meta": {
            "generated_at": generated_at,
            "schema": SNAPSHOT_SCHEMA,
            "force_refresh": force_refresh,
            "compact_mode": compact_mode,
            "runtime_mode": LIVE_RUNTIME_MODE,
            "loader_meta": raw.get("loader_meta", {}),
            "history_meta": history_meta,
            "snapshot_status": {
                "prior_generated_at": prior_manifest.get("generated_at"),
                "used_saved_snapshot": False,
                "history_store_present": history_meta.get("present", 0),
                "history_store_missing": history_meta.get("missing", 0),
            },
        },
        "shared_core": shared_core,
        "master_routes": master_routes,
        "master_opportunities": master_opportunities,
        "position_lifecycle": position_lifecycle,
        "home_summary": home_summary,
        "scenario_lab": scenario_lab,
        "dashboard": dashboard,
        "us": us,
        "ihsg": ihsg,
        "fx": fx,
        "commodities": commodities,
        "crypto": crypto,
        "scenarios": {
            "scenario_family": shared_core.get("scenario_family", []),
            "what_if_matrix": shared_core.get("what_if_matrix", {}),
            "dominant_news": shared_core.get("news_state", {}).get("display_state", "Quiet"),
            "shock_state": shared_core.get("shock", {}).get("state", "-"),
            "current_quad": shared_core.get("regime", {}).get("current_quad", "-"),
            "structural_quad": shared_core.get("regime_stack", {}).get("structural", {}).get("quad", shared_core.get("regime", {}).get("current_quad", "-")),
            "monthly_quad": shared_core.get("regime_stack", {}).get("monthly", {}).get("quad", "-"),
            "operating_regime": shared_core.get("resolved_regime", {}).get("operating_regime", "-"),
            "dominant_horizon": shared_core.get("resolved_regime", {}).get("dominant_horizon", "-"),
            "divergence_state": shared_core.get("resolved_regime", {}).get("divergence_state", "-"),
            "next_macro_countdown": shared_core.get("next_macro_summary", {}).get("countdown", "-"),
            "next_macro_family": shared_core.get("next_macro_summary", {}).get("family", "-"),
            "top_catalysts": shared_core.get("top_drivers", [])[:4],
            "petrodollar_state": shared_core.get("petrodollar", {}).get("state", "normal"),
            "petrodollar_score": shared_core.get("petrodollar", {}).get("score", 0.0),
            "market_winners_losers": {
                "us": us["strong_weak"],
                "ihsg": ihsg["strong_weak"],
                "fx": fx["strong_weak"],
                "commodities": commodities["strong_weak"],
                "crypto": crypto["strong_weak"],
            },
            "playbooks": shared_core.get("playbooks", []),
            "analogs": shared_core.get("analogs", []),
            "next_macro": shared_core.get("next_macro", []),
            "next_path": shared_core.get("next_path", {}),
            "master_graph": master_graph,
        },
        "master_graph": master_graph,
        "cross_asset": {
            "global_chain_map": transmissions,
            "conflict_map": shared_core.get("conflict_map", {}),
            "confirmation_map": shared_core.get("confirmation_map", {}),
            "rotation": shared_core.get("rotation", {}),
            "em_rotation": shared_core.get("em_rotation", {}),
            "petrodollar": shared_core.get('petrodollar', {}),
            "next_path": shared_core.get("next_path", {}),
            "master_graph": master_graph,
        },
        "diagnostics": {
            "data_quality": {
                "fred_series": len(raw.get("fred", {})),
                "price_series": len(raw.get("prices", {})),
                "news_items": len(raw.get("news", {}).get("top_headlines", [])) if isinstance(raw.get("news", {}), dict) else 0,
                "loader_meta": raw.get("loader_meta", {}),
                "structural_real_share": macro.get("structural_real_share", 0.0),
                "monthly_real_share": macro.get("monthly_real_share", 0.0),
                "monthly_data_coverage": macro.get("monthly_data_coverage", 0.0),
            },
            "shared_feature_coverage": {k: bool(v) for k, v in shared_features.items()},
            "native_feature_coverage": {k: bool(v) for k, v in native_features.items()},
            "coverage_reports": coverage_reports,
            "validation": shared_core.get("validation", {}),
            "news_state": shared_core.get("news_state", {}),
            "price_info": _price_info(raw.get("prices", {}), ["SPY", "^JKSE", "GC=F", "CL=F", "BTC-USD", "EURUSD=X"]),
            "events_library": raw.get("events", []),
            "macro_calendar": raw.get("macro_calendar", {}),
            "next_path": shared_core.get("next_path", {}),
            "flow_stack": shared_core.get("flow_stack", {}),
            "historical_analog_state": shared_core.get('historical_analog_state', {}),
            "scenario_tab_impact_map": shared_core.get('scenario_tab_impact_map', []),
            "master_graph": master_graph,
            "feature_integrity": {
                "macro_proxy_share": macro.get("macro_proxy_share", 0.0),
                "macro_real_share": macro.get("macro_real_share", 0.0),
                "fred_real_share": macro.get("fred_real_share", 0.0),
                "price_real_share": macro.get("price_real_share", 0.0),
                "structural_real_share": macro.get("structural_real_share", 0.0),
                "monthly_real_share": macro.get("monthly_real_share", 0.0),
                "monthly_data_coverage": macro.get("monthly_data_coverage", 0.0),
                "macro_confidence_penalty": macro.get("macro_confidence_penalty", 0.0),
                "proxy_used_count": macro.get("proxy_used_count", 0),
                "proxy_used_keys": macro.get("proxy_used_keys", []),
                "shared_core_integrity": shared_core.get("integrity", {}),
                "native_placeholders": {
                    "us": bool(native_features["us"].get("is_placeholder_heavy", True)),
                    "ihsg": bool(native_features["ihsg"].get("is_placeholder_heavy", True)),
                    "fx": bool(native_features["fx"].get("is_placeholder_heavy", True)),
                    "commodities": bool(native_features["commodities"].get("is_placeholder_heavy", True)),
                    "crypto": bool(native_features["crypto"].get("is_placeholder_heavy", True)),
                },
            },
            "risk_summary": shared_core.get("risk_summary", {}),
            "risk_range": shared_core.get("risk_range", {}),
            "tactical_components": shared_core.get("tactical_components", {}),
            "execution_components": shared_core.get("execution_mode", {}).get("score_components", {}),
            "raw_features": {
                "macro": macro,
                "market": market,
                "breadth": breadth,
                "vol_credit": vol_credit,
                "positioning": positioning,
                "derivatives": derivatives,
                "scenario": scenario,
                "plumbing": plumbing,
            },
        },
    }
    save_snapshot(snapshot)
    return snapshot


def _preview(sections: dict, key: str) -> list[dict]:
    rows = []
    for market_name, sec in sections.items():
        items = sec.get(key, [])[:2]
        for item in items:
            rows.append({"market": market_name, **item})
    return rows


def _strongest_markets(market_cards: dict) -> list[dict]:
    rows = []
    for name, card in market_cards.items():
        rows.append({"market": name.upper(), "score": float(card.get("score", 0.0)), "note": card.get("best_expression", "-")})
    return sorted(rows, key=lambda x: x["score"], reverse=True)


def _price_info(prices: dict, symbols: list[str]) -> dict:
    out = {}
    for sym in symbols:
        s = prices.get(sym)
        if s is None or getattr(s, "empty", True):
            continue
        try:
            out[sym] = {
                "last": float(s.iloc[-1]),
                "r21": float(s.iloc[-1] / s.iloc[-22] - 1) if len(s) >= 22 and s.iloc[-22] != 0 else 0.0,
            }
        except Exception:
            continue
    return out
