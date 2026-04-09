from __future__ import annotations

from config.asset_buckets import IHSG_BUCKETS
from config.universe_registry import IHSG_BACKEND_UNIVERSE, get_market_ranking_universe
from utils.math_utils import clamp01
from utils.ranking_utils import rank_symbols
from utils.ranking_context import ihsg_ranking_context
from features.market_features import ret_n


def build_ihsg_native_features(raw: dict, shared_core: dict) -> dict:
    prices = raw.get('prices', {})
    jkse_1m = ret_n(prices.get('^JKSE'), 21)
    spy_1m = ret_n(prices.get('SPY'), 21)
    usd_idr_1m = ret_n(prices.get('IDR=X'), 21)
    tlt_1m = ret_n(prices.get('TLT'), 21)

    ctx = ihsg_ranking_context(shared_core)
    bank_ranked, _ = rank_symbols(prices, IHSG_BUCKETS['Banks'], top_n=4, context=ctx)
    res_ranked, _ = rank_symbols(prices, IHSG_BUCKETS['Coal/Energy'] + IHSG_BUCKETS['Metals'], top_n=6, context=ctx)
    all_names = get_market_ranking_universe(IHSG_BUCKETS, IHSG_BACKEND_UNIVERSE)
    leaders, _ = rank_symbols(prices, all_names, top_n=12, context=ctx)

    bank_health = clamp01(0.5 + (sum(r['score'] for r in bank_ranked) / max(len(bank_ranked), 1)) / 0.20)
    commodity_spillover = clamp01(0.5 + (sum(r['score'] for r in res_ranked) / max(len(res_ranked), 1)) / 0.22)
    heavyweights = clamp01(0.5 + (sum(r['score'] for r in leaders[:5]) / max(len(leaders[:5]), 1)) / 0.18)

    bucket_scores = []
    positive = 0
    for _, syms in IHSG_BUCKETS.items():
        ranked, _ = rank_symbols(prices, syms, top_n=2, context=ctx)
        if ranked:
            score = sum(r['score'] for r in ranked) / len(ranked)
            bucket_scores.append(score)
            positive += 1 if score > 0 else 0
    breadth_liquidity = clamp01(0.55 * (positive / max(len(IHSG_BUCKETS), 1)) + 0.45 * clamp01(0.5 + jkse_1m / 0.08))

    global_risk = clamp01(0.45 * (1.0 - min(1.0, float(shared_core.get('risk_summary', {}).get('risk_off_score', 0)) / 4.0)) + 0.35 * shared_core.get('em_rotation', {}).get('score', 0.4) + 0.20 * shared_core.get('status_ribbon', {}).get('confidence', 0.5))
    usd_idr_pressure = clamp01(0.5 + usd_idr_1m / 0.08)
    indo_yield_pressure = clamp01(0.5 + max(0.0, -tlt_1m) / 0.05)
    bi_path_proxy = clamp01(0.60 - 0.35 * usd_idr_pressure - 0.25 * indo_yield_pressure + 0.20 * shared_core.get('em_rotation', {}).get('score', 0.4))
    foreign_flow = clamp01(0.35 * clamp01(0.5 + (jkse_1m - spy_1m) / 0.08) + 0.35 * heavyweights + 0.30 * bank_health)

    execution_score = clamp01(0.25 * global_risk + 0.20 * foreign_flow + 0.15 * breadth_liquidity + 0.15 * bank_health + 0.15 * commodity_spillover + 0.10 * (1.0 - usd_idr_pressure))
    execution_state = {
        'mode': 'Add on Reset' if execution_score >= 0.58 else ('Wait Reclaim' if execution_score >= 0.46 else 'Defensive / selective only'),
        'score': execution_score,
    }

    return {
        'prices': prices,
        'global_risk': global_risk,
        'usd_idr_pressure': usd_idr_pressure,
        'indo_yield_pressure': indo_yield_pressure,
        'bi_path_proxy': bi_path_proxy,
        'foreign_flow': foreign_flow,
        'breadth_liquidity': breadth_liquidity,
        'heavyweights': heavyweights,
        'bank_health': bank_health,
        'commodity_spillover': commodity_spillover,
        'execution_state': execution_state,
        'is_placeholder_heavy': False,
    }
