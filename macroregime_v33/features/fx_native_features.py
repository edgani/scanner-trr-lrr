from __future__ import annotations

from config.asset_buckets import FX_BUCKETS
from utils.math_utils import clamp01
from utils.ranking_utils import rank_symbols
from utils.ranking_context import fx_ranking_context
from features.market_features import ret_n


def build_fx_native_features(raw: dict, shared_core: dict) -> dict:
    prices = raw.get('prices', {})
    uup_1m = ret_n(prices.get('UUP'), 21)
    tlt_1m = ret_n(prices.get('TLT'), 21)
    gold_1m = ret_n(prices.get('GC=F'), 21)
    oil_1m = ret_n(prices.get('CL=F'), 21)

    ctx = fx_ranking_context(shared_core)
    majors, _ = rank_symbols(prices, FX_BUCKETS['Majors'], top_n=7, context=ctx)
    jpy_crosses, _ = rank_symbols(prices, FX_BUCKETS['JPY Crosses'], top_n=4, context=ctx)
    asia, _ = rank_symbols(prices, FX_BUCKETS['Asia Overlay'], top_n=3, context=ctx)

    majors_score = sum(r['score'] for r in majors) / max(len(majors), 1)
    jpy_score = sum(r['score'] for r in jpy_crosses) / max(len(jpy_crosses), 1)
    asia_score = sum(r['score'] for r in asia) / max(len(asia), 1)
    valid_pairs = len(majors) + len(jpy_crosses) + len(asia)

    rate_diff = clamp01(0.5 + (uup_1m - tlt_1m) / 0.08)
    real_rate_diff = clamp01(0.5 + (uup_1m - gold_1m) / 0.10)
    macro_surprise_diff = clamp01(0.45 * shared_core.get('status_ribbon', {}).get('confidence', 0.5) + 0.35 * shared_core.get('weather', {}).get('score', 0.5) + 0.20 * (1.0 - min(1.0, float(shared_core.get('risk_summary', {}).get('risk_off_score', 0)) / 4.0)))
    external_balance_tot = clamp01(0.45 * clamp01(0.5 + oil_1m / 0.12) + 0.30 * clamp01(0.5 + majors_score / 0.18) + 0.25 * clamp01(0.5 + asia_score / 0.18))

    intervention_risk = clamp01(0.35 * clamp01(0.5 + max(0.0, uup_1m) / 0.05) + 0.30 * shared_core.get('risk_summary', {}).get('crash_score', 0) / 6.0 + 0.20 * max(0.0, -asia_score) / 0.18 + 0.15 * max(0.0, -jpy_score) / 0.18)
    positioning_heat = clamp01(shared_core.get('positioning', {}).get('crowding_proxy', 0.5))
    options_heat = clamp01(shared_core.get('vix_bucket', {}).get('tail_hedge_bid', 0.5))
    liquidity_quality = clamp01(0.45 * clamp01(0.5 + majors_score / 0.18) + 0.25 * (1.0 - intervention_risk) + 0.30 * (1.0 - min(1.0, float(shared_core.get('risk_summary', {}).get('risk_off_score', 0)) / 4.0)))

    direction_score = clamp01(0.28 * rate_diff + 0.18 * real_rate_diff + 0.18 * macro_surprise_diff + 0.16 * external_balance_tot + 0.10 * (1.0 - intervention_risk) + 0.10 * liquidity_quality)
    execution_state = {
        'mode': 'Long Now' if direction_score >= 0.60 and intervention_risk < 0.55 else ('Wait Reclaim' if direction_score >= 0.48 else 'Two-way / tactical only'),
        'score': direction_score,
    }

    return {
        'prices': prices,
        'rate_diff': rate_diff,
        'real_rate_diff': real_rate_diff,
        'macro_surprise_diff': macro_surprise_diff,
        'external_balance_tot': external_balance_tot,
        'intervention_risk': intervention_risk,
        'positioning_heat': positioning_heat,
        'options_heat': options_heat,
        'liquidity_quality': liquidity_quality,
        'pair_breadth': clamp01(0.5 + majors_score / 0.18),
        'execution_state': execution_state,
        'is_placeholder_heavy': valid_pairs < 5,
    }
