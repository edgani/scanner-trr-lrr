from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
import math

from config.family_map import classify_symbol, manifest_record
from config.regime_policy import QUAD_POLICY, SHORTLIST_POLICY, FAMILY_CAPS
from config.route_policy import ROUTE_POLICY
from data.history_store import read_manifest
from config.universe_registry import (
    US_BACKEND_UNIVERSE, IHSG_BACKEND_UNIVERSE, FX_BACKEND_UNIVERSE,
    COMMODITIES_BACKEND_UNIVERSE, CRYPTO_BACKEND_UNIVERSE,
    US_CURATED_BACKEND_UNIVERSE, IHSG_CURATED_BACKEND_UNIVERSE, FX_CURATED_BACKEND_UNIVERSE,
    COMMODITIES_CURATED_BACKEND_UNIVERSE, CRYPTO_CURATED_BACKEND_UNIVERSE,
)


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


def _days_stale(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        today = datetime.now(timezone.utc)
        return max(0, int((today.date() - dt.date()).days))
    except Exception:
        return None


def derive_route_state(shared_core: dict | None) -> dict[str, Any]:
    shared_core = shared_core or {}
    ribbon = shared_core.get('status_ribbon', {}) or {}
    structural = str(ribbon.get('structural_quad', 'Q3'))
    monthly = str(ribbon.get('monthly_quad', structural))
    divergence = str(ribbon.get('divergence_state', 'aligned' if structural == monthly else 'divergent'))
    risk = shared_core.get('risk_summary', {}) or {}
    execution = shared_core.get('execution_mode', {}) or {}
    weather = shared_core.get('weather', {}) or {}
    news_state = str((shared_core.get('news_state', {}) or {}).get('state', 'quiet'))

    risk_off = _clamp(risk.get('risk_off_score', 0.5))
    crash = _clamp(risk.get('crash_score', 0.25))
    exec_score = _clamp(execution.get('score', 0.5))
    weather_score = _clamp(weather.get('score', 0.5))
    tail_state = str(weather.get('tail_state', 'neutral'))

    if crash >= 0.75 or news_state in {'panic', 'crash', 'liquidity_freeze'}:
        primary = 'panic_crash'
        alt = 'vshape_rebound'
    elif structural == 'Q4' or risk_off >= 0.68:
        primary = 'deflationary_riskoff'
        alt = 'vshape_rebound' if exec_score >= 0.52 else 'reflation_reaccel'
    elif structural == 'Q3' and (monthly in {'Q3', 'Q4'} or tail_state == 'stressed'):
        primary = 'stagflation_persist'
        alt = 'growth_scare' if risk_off >= 0.58 else 'reflation_reaccel'
    elif monthly == 'Q2' and exec_score >= 0.55 and weather_score >= 0.55:
        primary = 'reflation_reaccel'
        alt = 'growth_scare'
    elif structural == 'Q1' and weather_score >= 0.52:
        primary = 'quality_disinflation'
        alt = 'reflation_reaccel'
    else:
        primary = 'growth_scare' if risk_off >= 0.55 else 'quality_disinflation'
        alt = 'reflation_reaccel' if primary != 'reflation_reaccel' else 'growth_scare'

    if divergence == 'divergent' and monthly == 'Q2' and exec_score >= 0.56 and weather_score >= 0.56:
        alt = 'reflation_reaccel'
    if divergence == 'divergent' and monthly == 'Q4' and risk_off >= 0.58:
        alt = 'vshape_rebound' if primary == 'deflationary_riskoff' else 'deflationary_riskoff'
    if alt == primary:
        alt = 'vshape_rebound' if primary != 'vshape_rebound' else 'reflation_reaccel'

    return {
        'structural_quad': structural,
        'monthly_quad': monthly,
        'divergence_state': divergence,
        'primary_route': primary,
        'alt_route': alt,
        'risk_off_score': risk_off,
        'crash_score': crash,
        'execution_score': exec_score,
        'weather_score': weather_score,
        'news_state': news_state,
    }


def _policy(market: str, route_state: dict[str, Any]) -> dict[str, list[str]]:
    market = str(market).lower().strip()
    structural = str(route_state.get('structural_quad', 'Q3'))
    monthly = str(route_state.get('monthly_quad', structural))
    primary = str(route_state.get('primary_route', 'growth_scare'))
    alt = str(route_state.get('alt_route', 'vshape_rebound'))

    qpol = QUAD_POLICY.get(monthly) or QUAD_POLICY.get(structural) or {}
    qcur = dict(qpol.get(market, {}) or {})
    rpri = dict((ROUTE_POLICY.get(primary, {}) or {}).get(market, {}) or {})
    ralt = dict((ROUTE_POLICY.get(alt, {}) or {}).get(market, {}) or {})

    def merged(key: str) -> list[str]:
        out: list[str] = []
        for part in (qcur.get(key, []), rpri.get(key, [])):
            for fam in part:
                if fam not in out:
                    out.append(fam)
        return out

    return {
        'boost': merged('boost'),
        'cut': merged('cut'),
        'short': merged('short'),
        'safe_harbor': merged('safe_harbor'),
        'alt_boost': list(ralt.get('boost', []) or []),
        'primary_route': primary,
        'alt_route': alt,
        'structural_quad': structural,
        'monthly_quad': monthly,
    }




def _flatten(node) -> list[str]:
    if isinstance(node, dict):
        out: list[str] = []
        for v in node.values():
            out.extend(_flatten(v))
        return out
    if isinstance(node, (list, tuple, set)):
        out: list[str] = []
        for v in node:
            out.extend(_flatten(v))
        return out
    return [str(node).strip()] if str(node).strip() else []

def _market_sets(market: str) -> tuple[list[str], list[str]]:
    m = str(market).lower().strip()
    if m == 'us':
        return _flatten(US_BACKEND_UNIVERSE), _flatten(US_CURATED_BACKEND_UNIVERSE)
    if m == 'ihsg':
        return _flatten(IHSG_BACKEND_UNIVERSE), _flatten(IHSG_CURATED_BACKEND_UNIVERSE)
    if m == 'fx':
        return _flatten(FX_BACKEND_UNIVERSE), _flatten(FX_CURATED_BACKEND_UNIVERSE)
    if m == 'commodities':
        return _flatten(COMMODITIES_BACKEND_UNIVERSE), _flatten(COMMODITIES_CURATED_BACKEND_UNIVERSE)
    if m == 'crypto':
        return _flatten(CRYPTO_BACKEND_UNIVERSE), _flatten(CRYPTO_CURATED_BACKEND_UNIVERSE)
    return [], []


def _history_quality(info: dict[str, Any]) -> tuple[float, float, float]:
    rows = int((info or {}).get('rows', 0) or 0)
    stale = _days_stale((info or {}).get('last_date'))
    freshness = 0.35
    if stale is None:
        freshness = 0.35
    elif stale <= 3:
        freshness = 1.0
    elif stale <= 7:
        freshness = 0.82
    elif stale <= 14:
        freshness = 0.62
    elif stale <= 30:
        freshness = 0.42
    else:
        freshness = 0.22
    coverage = 1.0 if rows >= 252 else 0.85 if rows >= 180 else 0.65 if rows >= 120 else 0.48 if rows >= 60 else 0.25 if rows > 0 else 0.0
    # summary metrics are optional and get stronger when history_store manifest was refreshed under the new schema.
    ret20 = float((info or {}).get('ret_20d', 0.0) or 0.0)
    ret63 = float((info or {}).get('ret_63d', 0.0) or 0.0)
    trend = 0.50 + 0.20 * math.tanh(ret20 / 0.18) + 0.20 * math.tanh(ret63 / 0.30)
    return _clamp(coverage), _clamp(freshness), _clamp(trend)


def _liquidity_quality(market: str, symbol: str, family: str, traits: set[str]) -> float:
    rec = manifest_record(market, symbol)
    if market == 'us':
        if 'junk_structure' in traits:
            return 0.05
        if rec.get('is_etf'):
            return 0.72
        return 0.58 if family not in {'small_beta', 'unclassified'} else 0.44
    if market == 'ihsg':
        shares = float(rec.get('shares', 0.0) or 0.0)
        quality = 0.60 if shares >= 5e9 else 0.52 if shares >= 1e9 else 0.42
        board = str(rec.get('listing_board', '')).lower()
        if 'pemantauan' in board:
            quality -= 0.18
        return _clamp(quality)
    if market == 'crypto':
        if family in {'btc_quality', 'majors'}:
            return 0.72
        if family in {'high_beta', 'micro_alt'}:
            return 0.28
        return 0.48
    if market == 'fx':
        return 0.82 if family in {'majors', 'defensive_usd'} else 0.66
    if market == 'commodities':
        return 0.74 if family in {'precious', 'energy', 'industrial'} else 0.60
    return 0.5


def _theme_alignment(market: str, family: str, route_state: dict[str, Any]) -> float:
    primary = str(route_state.get('primary_route', 'growth_scare'))
    if market == 'crypto' and primary in {'reflation_reaccel', 'vshape_rebound'} and family in {'ai_data', 'infra', 'high_beta'}:
        return 0.75
    if market == 'us' and primary == 'reflation_reaccel' and family in {'semis', 'growth', 'industrials'}:
        return 0.70
    if market == 'commodities' and primary in {'stagflation_persist', 'reflation_reaccel'} and family in {'energy', 'precious'}:
        return 0.70
    return 0.50


def _fragility_penalty(market: str, family: str, traits: set[str], route_state: dict[str, Any]) -> float:
    risk_off = float(route_state.get('risk_off_score', 0.5) or 0.5)
    crash = float(route_state.get('crash_score', 0.25) or 0.25)
    p = 0.0
    if 'junk_structure' in traits or 'special_board' in traits:
        p += 0.50
    if family in {'small_beta', 'micro_alt', 'high_beta'}:
        p += 0.28
    if family in {'consumer_cyc', 'carry_beta', 'asia_beta'} and risk_off >= 0.55:
        p += 0.18
    if crash >= 0.65 and family in {'high_beta', 'micro_alt', 'small_beta'}:
        p += 0.20
    return _clamp(p)


def _crowding_penalty(market: str, family: str, route_state: dict[str, Any]) -> float:
    primary = str(route_state.get('primary_route', 'growth_scare'))
    if primary in {'reflation_reaccel', 'vshape_rebound'} and family in {'growth', 'semis', 'ai_data', 'high_beta'}:
        return 0.12
    if primary in {'stagflation_persist'} and family in {'energy', 'precious'}:
        return 0.08
    return 0.03


def _market_local_fit(market: str, family: str, traits: set[str], route_state: dict[str, Any]) -> float:
    risk_off = float(route_state.get('risk_off_score', 0.5) or 0.5)
    if market == 'ihsg':
        if 'exporter' in traits and route_state.get('primary_route') in {'stagflation_persist', 'reflation_reaccel'}:
            return 0.72
        if 'import_sensitive' in traits and risk_off >= 0.55:
            return 0.28
    if market == 'fx':
        if family == 'defensive_usd' and risk_off >= 0.55:
            return 0.75
        if family == 'commodity_fx' and route_state.get('primary_route') == 'reflation_reaccel':
            return 0.72
    if market == 'crypto':
        if route_state.get('primary_route') in {'deflationary_riskoff', 'panic_crash'} and family in {'high_beta', 'micro_alt'}:
            return 0.20
    return 0.50


def _label_for_symbol(family: str, policy: dict[str, Any], traits: set[str]) -> str:
    if family in set(policy.get('safe_harbor', [])):
        return 'safe_harbor'
    if family in set(policy.get('short', [])) or 'junk_structure' in traits or 'special_board' in traits:
        return 'shorts'
    if family in set(policy.get('alt_boost', [])):
        return 'alt_route'
    if family in set(policy.get('boost', [])):
        return 'best_now'
    return 'next_route'


def _allow_symbol(market: str, symbol: str, family: str, traits: set[str], curated_set: set[str], hist_info: dict[str, Any]) -> bool:
    rows = int((hist_info or {}).get('rows', 0) or 0)
    if symbol in curated_set:
        return True
    if market == 'us' and 'junk_structure' in traits:
        return False
    if market == 'crypto' and ('leveraged_token' in traits or (family == 'micro_alt' and rows < 120)):
        return False
    if market == 'ihsg' and 'special_board' in traits and rows < 120:
        return False
    return True


def _coarse_score(market: str, symbol: str, family: str, traits: set[str], policy: dict[str, Any], hist_info: dict[str, Any], curated: bool, route_state: dict[str, Any]) -> tuple[float, dict[str, float]]:
    history_score, freshness_score, trend_score = _history_quality(hist_info)
    regime_fit = 0.5
    if family in set(policy.get('boost', [])):
        regime_fit += 0.28
    if family in set(policy.get('safe_harbor', [])):
        regime_fit += 0.14
    if family in set(policy.get('cut', [])):
        regime_fit -= 0.18
    next_route_fit = 0.72 if family in set(policy.get('boost', [])) else 0.58 if family in set(policy.get('alt_boost', [])) else 0.42
    alt_route_robustness = 0.74 if family in set(policy.get('safe_harbor', [])) else 0.58 if family in set(policy.get('alt_boost', [])) else 0.42
    local_macro_fit = _market_local_fit(market, family, traits, route_state)
    simple_price_health = 0.55 * trend_score + 0.25 * history_score + 0.20 * freshness_score
    liquidity_quality = _liquidity_quality(market, symbol, family, traits)
    theme_alignment = _theme_alignment(market, family, route_state)
    fragility_penalty = _fragility_penalty(market, family, traits, route_state)
    crowding_penalty = _crowding_penalty(market, family, route_state)
    curated_bonus = 0.12 if curated else 0.0
    score = (
        0.30 * regime_fit
        + 0.20 * next_route_fit
        + 0.10 * alt_route_robustness
        + 0.15 * local_macro_fit
        + 0.10 * simple_price_health
        + 0.10 * liquidity_quality
        + 0.05 * theme_alignment
        + curated_bonus
        - 0.15 * fragility_penalty
        - 0.10 * crowding_penalty
    )
    components = {
        'regime_fit': _clamp(regime_fit),
        'next_route_fit': _clamp(next_route_fit),
        'alt_route_robustness': _clamp(alt_route_robustness),
        'local_macro_fit': _clamp(local_macro_fit),
        'simple_price_health': _clamp(simple_price_health),
        'liquidity_quality': _clamp(liquidity_quality),
        'theme_alignment': _clamp(theme_alignment),
        'fragility_penalty': _clamp(fragility_penalty),
        'crowding_penalty': _clamp(crowding_penalty),
        'history_score': _clamp(history_score),
        'freshness_score': _clamp(freshness_score),
        'trend_score': _clamp(trend_score),
    }
    return float(score), components


def _dedup(seq: list[str]) -> list[str]:
    out: list[str] = []
    for s in seq:
        sx = str(s).strip()
        if sx and sx not in out:
            out.append(sx)
    return out


def _compact_limit(market: str, default_limits: dict[str, int] | None = None) -> int:
    base = {'us': 250, 'ihsg': 150, 'fx': 16, 'commodities': 24, 'crypto': 200}
    if default_limits:
        base.update({k: int(v) for k, v in default_limits.items()})
    return int(base.get(market, 50))


def select_market_runtime(market: str, route_state: dict[str, Any], compact_limit: int | None = None) -> tuple[list[str], dict[str, Any]]:
    backend, curated = _market_sets(market)
    backend = _dedup(backend)
    curated = _dedup(curated)
    candidates = _dedup(curated + backend)
    curated_set = set(curated)
    hist_store = (read_manifest() or {}).get('symbols', {}) or {}
    policy = _policy(market, route_state)
    label_quota = dict(SHORTLIST_POLICY.get(market, {}))
    family_cap = int(FAMILY_CAPS.get(market, 12))
    limit = int(compact_limit or _compact_limit(market))

    if market in {'fx', 'commodities'}:
        # Small enough to keep fully visible even in compact mode.
        out = backend[:limit] if limit < len(backend) else list(backend)
        return out, {
            'market': market,
            'method': 'small_market_passthrough',
            'limit': limit,
            'selected': len(out),
            'backend_count': len(backend),
            'candidate_count': len(candidates),
            'route_state': route_state,
        }

    scored: list[dict[str, Any]] = []
    pass0_rejects = 0
    for sym in candidates:
        family, traits = classify_symbol(market, sym)
        info = dict(hist_store.get(sym, {}) or {})
        if not _allow_symbol(market, sym, family, traits, curated_set, info):
            pass0_rejects += 1
            continue
        score, components = _coarse_score(market, sym, family, traits, policy, info, sym in curated_set, route_state)
        label = _label_for_symbol(family, policy, traits)
        scored.append({
            'symbol': sym,
            'family': family,
            'traits': sorted(traits),
            'label': label,
            'score': score,
            'curated': sym in curated_set,
            'components': components,
        })

    scored.sort(key=lambda row: (row['score'], row['curated']), reverse=True)
    selected: list[str] = []
    selected_rows: list[dict[str, Any]] = []
    family_counts: dict[str, int] = defaultdict(int)

    def _try_take(rows: list[dict[str, Any]], wanted: int, enforce_family_cap: bool = True):
        for row in rows:
            if len(selected) >= limit or wanted <= 0:
                break
            sym = row['symbol']
            fam = row['family']
            if sym in selected:
                continue
            if enforce_family_cap and family_counts[fam] >= family_cap:
                continue
            selected.append(sym)
            selected_rows.append(row)
            family_counts[fam] += 1
            wanted -= 1

    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in scored:
        by_label[row['label']].append(row)

    # Curated leaders remain the front door, but selection becomes regime-aware and diversified.
    for label in ('best_now', 'safe_harbor', 'next_route', 'shorts', 'alt_route'):
        _try_take(by_label.get(label, []), int(label_quota.get(label, 0)))

    # Fill remaining slots with highest-score names, then relax family cap if still short.
    _try_take(scored, limit - len(selected), enforce_family_cap=True)
    if len(selected) < limit:
        _try_take(scored, limit - len(selected), enforce_family_cap=False)

    meta = {
        'market': market,
        'method': 'route_aware_compact_v1',
        'limit': limit,
        'selected': len(selected),
        'backend_count': len(backend),
            'candidate_count': len(candidates),
        'pass0_rejects': pass0_rejects,
        'route_state': route_state,
        'policy': {
            'boost': policy.get('boost', []),
            'safe_harbor': policy.get('safe_harbor', []),
            'short': policy.get('short', []),
            'alt_boost': policy.get('alt_boost', []),
        },
        'label_counts': {label: sum(1 for r in selected_rows if r['label'] == label) for label in ('best_now', 'safe_harbor', 'next_route', 'shorts', 'alt_route')},
        'family_counts': dict(sorted(family_counts.items(), key=lambda kv: kv[1], reverse=True)[:12]),
        'sample_rows': [
            {
                'symbol': r['symbol'],
                'label': r['label'],
                'family': r['family'],
                'score': round(float(r['score']), 4),
            }
            for r in selected_rows[:15]
        ],
    }
    return selected, meta


def select_runtime_universe(compact_mode: bool, route_state: dict[str, Any], limits: dict[str, int] | None = None) -> tuple[dict[str, list[str]], dict[str, Any]]:
    if not compact_mode:
        out = {
            'us': _market_sets('us')[0],
            'ihsg': _market_sets('ihsg')[0],
            'fx': _market_sets('fx')[0],
            'commodities': _market_sets('commodities')[0],
            'crypto': _market_sets('crypto')[0],
        }
        meta = {
            'method': 'full_backend_passthrough',
            'route_state': route_state,
            'markets': {k: {'selected': len(v), 'backend_count': len(v)} for k, v in out.items()},
        }
        return out, meta

    limits = limits or {}
    out: dict[str, list[str]] = {}
    markets_meta: dict[str, Any] = {}
    for market in ('us', 'ihsg', 'fx', 'commodities', 'crypto'):
        selected, meta = select_market_runtime(market, route_state, compact_limit=int(limits.get(market, 0) or _compact_limit(market, limits)))
        out[market] = selected
        markets_meta[market] = meta
    return out, {
        'method': 'route_aware_compact_v1',
        'route_state': route_state,
        'markets': markets_meta,
    }
