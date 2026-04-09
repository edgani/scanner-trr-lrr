from __future__ import annotations

from config.asset_buckets import US_BUCKETS
from config.universe_registry import US_BACKEND_UNIVERSE, get_market_ranking_universe
from utils.math_utils import clamp01
from utils.ranking_utils import rank_symbols
from utils.ranking_context import us_ranking_context
from features.market_features import ret_n


MAG7 = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA']
STYLE_BREADTH = {
    'Growth': ['QQQ', 'VUG'],
    'Value': ['VTV', 'IWD'],
    'Quality': ['QUAL'],
    'High Beta': ['SPHB'],
}


def build_us_equity_features(raw: dict, shared_core: dict) -> dict:
    prices = raw.get('prices', {})
    universe = get_market_ranking_universe(US_BUCKETS, US_BACKEND_UNIVERSE)
    ctx = us_ranking_context(shared_core)
    strong, weak = rank_symbols(prices, universe, top_n=12, context=ctx)

    spy_1m = ret_n(prices.get('SPY'), 21)
    rsp_rel = ret_n(prices.get('RSP'), 21) - spy_1m
    iwm_rel = ret_n(prices.get('IWM'), 21) - spy_1m

    sector_scores = {}
    positive = 0
    valid = 0
    for bucket, syms in US_BUCKETS.items():
        ranked, _ = rank_symbols(prices, syms, top_n=3, context=ctx)
        if ranked:
            score = sum(r['score'] for r in ranked) / len(ranked)
            sector_scores[bucket] = score
            valid += 1
            positive += 1 if score > 0 else 0
        else:
            sector_scores[bucket] = 0.0
    sector_breadth_score = positive / max(valid, 1)

    mag7_ranked, _ = rank_symbols(prices, MAG7, top_n=7, context=ctx)
    mag7_score = sum(r['score'] for r in mag7_ranked) / max(len(mag7_ranked), 1)
    broad_score = sum(sector_scores.values()) / max(len(sector_scores), 1)
    mag7_concentration = clamp01(0.5 + (mag7_score - broad_score) / 0.20)

    breadth_health = clamp01(0.50 * sector_breadth_score + 0.25 * clamp01(0.5 + rsp_rel / 0.05) + 0.25 * clamp01(0.5 + iwm_rel / 0.06))
    eqw_health = clamp01(0.5 + rsp_rel / 0.05)
    smallcap_health = clamp01(0.5 + iwm_rel / 0.06)

    risk = shared_core.get('risk_summary', {})
    crash_pen = min(1.0, float(risk.get('crash_score', 0)) / 6.0) if risk.get('crash_score') is not None else 0.5
    vol_bucket = str(shared_core.get('vix_bucket', {}).get('bucket', 'Unknown'))
    vol_ok = 0.78 if vol_bucket == 'Investable' else 0.52 if vol_bucket == 'Chop' else 0.26
    credit_ok = clamp01(0.55 * (1.0 - crash_pen) + 0.25 * shared_core.get('weather', {}).get('tail_score', 0.5) + 0.20 * shared_core.get('weather', {}).get('trade_score', 0.5))

    execution_score = clamp01(0.5 * shared_core.get('execution_mode', {}).get('score', 0.5) + 0.3 * shared_core.get('status_ribbon', {}).get('confidence', 0.5) + 0.2 * (1.0 - crash_pen))
    execution_state = {
        'mode': shared_core.get('execution_mode', {}).get('execute_mode', 'Selective adds only'),
        'score': execution_score,
    }

    return {
        'prices': prices,
        'sector_breadth': US_BUCKETS,
        'style_breadth': STYLE_BREADTH,
        'mag7_concentration': mag7_concentration,
        'strong_names_seed': strong,
        'weak_names_seed': weak,
        'breadth_health': breadth_health,
        'eqw_health': eqw_health,
        'smallcap_health': smallcap_health,
        'credit_ok': credit_ok,
        'vol_ok': vol_ok,
        'sector_breadth_score': sector_breadth_score,
        'execution_state': execution_state,
        'is_placeholder_heavy': False,
    }
