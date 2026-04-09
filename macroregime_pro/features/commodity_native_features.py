from __future__ import annotations

from config.asset_buckets import COMMODITY_BUCKETS
from config.universe_registry import COMMODITIES_BACKEND_UNIVERSE, get_market_ranking_universe
from utils.math_utils import clamp01
from utils.ranking_utils import rank_symbols
from utils.ranking_context import commodity_ranking_context
from features.market_features import ret_n


def _avg_score(rows: list[dict]) -> float:
    return sum(r['score'] for r in rows) / max(len(rows), 1)


def build_commodity_native_features(raw: dict, shared_core: dict) -> dict:
    prices = raw.get('prices', {})
    all_syms = get_market_ranking_universe(COMMODITY_BUCKETS, COMMODITIES_BACKEND_UNIVERSE)
    ctx = commodity_ranking_context(shared_core)
    leaders, _ = rank_symbols(prices, all_syms, top_n=18, context=ctx)

    energy, _ = rank_symbols(prices, COMMODITY_BUCKETS['Energy'], top_n=5, context=ctx)
    precious, _ = rank_symbols(prices, COMMODITY_BUCKETS['Precious'], top_n=4, context=ctx)
    industrial, _ = rank_symbols(prices, COMMODITY_BUCKETS['Industrial'] + COMMODITY_BUCKETS['Broad Proxies'], top_n=4, context=ctx)
    agri, _ = rank_symbols(prices, COMMODITY_BUCKETS['Agri/Softs'], top_n=5, context=ctx)

    energy_score = _avg_score(energy)
    precious_score = _avg_score(precious)
    industrial_score = _avg_score(industrial)
    agri_score = _avg_score(agri)

    gold_1m = ret_n(prices.get('GC=F'), 21)
    wti_1m = ret_n(prices.get('CL=F'), 21)
    wti_3m = ret_n(prices.get('CL=F'), 63)
    hg_1m = ret_n(prices.get('HG=F'), 21)
    uup_1m = ret_n(prices.get('UUP'), 21)
    tlt_1m = ret_n(prices.get('TLT'), 21)

    physical_balance = clamp01(0.30 * clamp01(0.5 + energy_score / 0.18) + 0.25 * clamp01(0.5 + industrial_score / 0.16) + 0.20 * clamp01(0.5 + agri_score / 0.16) + 0.25 * clamp01(0.5 + (leaders[0]['score'] if leaders else 0.0) / 0.20))
    inventory_stress = clamp01(0.35 * clamp01(0.5 + wti_1m / 0.14) + 0.25 * clamp01(0.5 + hg_1m / 0.12) + 0.20 * clamp01(0.5 + energy_score / 0.18) + 0.20 * clamp01(0.5 + industrial_score / 0.16))
    curve_tightness = clamp01(0.45 * clamp01(0.5 + (wti_1m - 0.5 * wti_3m) / 0.12) + 0.30 * clamp01(0.5 + gold_1m / 0.10) + 0.25 * clamp01(0.5 + energy_score / 0.18))
    positioning_vol = clamp01(0.55 * shared_core.get('positioning', {}).get('crowding_proxy', 0.5) + 0.45 * shared_core.get('vix_bucket', {}).get('tail_hedge_bid', 0.5))
    usd_rates_pressure = clamp01(0.60 * clamp01(0.5 + uup_1m / 0.04) + 0.40 * clamp01(0.5 + max(0.0, -tlt_1m) / 0.05))

    dominant = str(shared_core.get('news_state', {}).get('state', 'quiet'))
    exogenous_shock = clamp01(0.50 * clamp01(0.5 + wti_1m / 0.14) + 0.25 * (1.0 if dominant == 'war_oil' else 0.25) + 0.25 * shared_core.get('risk_summary', {}).get('crash_score', 0) / 6.0)

    native_score = clamp01(0.24 * physical_balance + 0.20 * inventory_stress + 0.16 * curve_tightness + 0.16 * (1.0 - usd_rates_pressure) + 0.12 * exogenous_shock + 0.12 * (1.0 - positioning_vol))
    execution_state = {
        'mode': 'Long Now' if native_score >= 0.60 and usd_rates_pressure < 0.62 else ('Wait Reset' if native_score >= 0.48 else 'Two-way / tactical only'),
        'score': native_score,
    }

    return {
        'prices': prices,
        'physical_balance': physical_balance,
        'inventory_stress': inventory_stress,
        'curve_tightness': curve_tightness,
        'positioning_vol': positioning_vol,
        'usd_rates_pressure': usd_rates_pressure,
        'exogenous_shock': exogenous_shock,
        'precious_strength': clamp01(0.5 + precious_score / 0.16),
        'energy_strength': clamp01(0.5 + energy_score / 0.18),
        'execution_state': execution_state,
        'is_placeholder_heavy': len(leaders) < 6,
    }
