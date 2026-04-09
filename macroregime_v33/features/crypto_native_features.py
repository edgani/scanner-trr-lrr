from __future__ import annotations

from config.asset_buckets import CRYPTO_BUCKETS
from config.universe_registry import CRYPTO_BACKEND_UNIVERSE, get_market_ranking_universe
from utils.math_utils import clamp01
from utils.ranking_utils import rank_symbols
from utils.ranking_context import crypto_ranking_context


def _bucket_score(prices: dict, syms: list[str], top_n: int = 4, context: dict | None = None) -> float:
    ranked, _ = rank_symbols(prices, syms, top_n=top_n, context=context)
    return sum(r['score'] for r in ranked) / max(len(ranked), 1)


def build_crypto_native_features(raw: dict, shared_core: dict) -> dict:
    prices = raw.get('prices', {})
    all_syms = get_market_ranking_universe(CRYPTO_BUCKETS, CRYPTO_BACKEND_UNIVERSE)
    ctx = crypto_ranking_context(shared_core)
    leaders, _ = rank_symbols(prices, all_syms, top_n=18, context=ctx)

    majors_score = _bucket_score(prices, CRYPTO_BUCKETS['Majors'], 5, context=ctx)
    high_beta_score = _bucket_score(prices, CRYPTO_BUCKETS['High Beta'], 5, context=ctx)
    ai_score = _bucket_score(prices, CRYPTO_BUCKETS['AI/Data'], 4, context=ctx)
    rwa_score = _bucket_score(prices, CRYPTO_BUCKETS['RWA'], 2, context=ctx)
    infra_score = _bucket_score(prices, CRYPTO_BUCKETS['Infra'], 5, context=ctx)
    defi_score = _bucket_score(prices, CRYPTO_BUCKETS['DeFi'], 4, context=ctx)

    bucket_scores = [majors_score, high_beta_score, ai_score, rwa_score, infra_score, defi_score]
    positive_ratio = sum(1 for x in bucket_scores if x > 0) / max(len(bucket_scores), 1)
    breadth_score = clamp01(0.5 + (sum(bucket_scores) / len(bucket_scores)) / 0.20)

    flow = clamp01(0.40 * breadth_score + 0.30 * clamp01(0.5 + majors_score / 0.18) + 0.30 * positive_ratio)
    usage = clamp01(0.40 * clamp01(0.5 + infra_score / 0.18) + 0.35 * clamp01(0.5 + defi_score / 0.18) + 0.25 * positive_ratio)
    supply_tightness = clamp01(0.50 * clamp01(0.5 + majors_score / 0.18) + 0.25 * breadth_score + 0.25 * (1.0 - shared_core.get('risk_summary', {}).get('risk_off_score', 0) / 4.0))
    supply_overhang = clamp01(0.45 * (1.0 - breadth_score) + 0.25 * max(0.0, -high_beta_score) / 0.20 + 0.15 * shared_core.get('positioning', {}).get('unwind_risk_proxy', 0.5) + 0.15 * shared_core.get('vix_bucket', {}).get('tail_hedge_bid', 0.5))
    leverage_heat = clamp01(0.35 * clamp01(0.5 + (high_beta_score - majors_score) / 0.20) + 0.35 * shared_core.get('positioning', {}).get('crowding_proxy', 0.5) + 0.30 * shared_core.get('vix_bucket', {}).get('tail_hedge_bid', 0.5))
    liquidity_fragility = clamp01(0.40 * (1.0 - breadth_score) + 0.30 * shared_core.get('risk_summary', {}).get('crash_score', 0) / 6.0 + 0.30 * supply_overhang)
    holder_state = clamp01(0.60 * clamp01(0.5 + majors_score / 0.18) + 0.40 * positive_ratio)
    narrative = clamp01(0.35 * clamp01(0.5 + ai_score / 0.18) + 0.20 * clamp01(0.5 + rwa_score / 0.18) + 0.25 * clamp01(0.5 + infra_score / 0.18) + 0.20 * clamp01(0.5 + defi_score / 0.18))

    news_state = str(shared_core.get('news_state', {}).get('state', 'quiet'))
    trust_penalty = clamp01(0.40 * shared_core.get('risk_summary', {}).get('crash_score', 0) / 6.0 + 0.30 * (1.0 if news_state in {'policy_pressure', 'war_oil'} else 0.20) + 0.30 * supply_overhang)

    execution_score = clamp01(0.24 * flow + 0.16 * usage + 0.14 * supply_tightness + 0.14 * narrative + 0.12 * holder_state + 0.10 * (1.0 - liquidity_fragility) + 0.10 * (1.0 - trust_penalty))
    risk_mode = str(shared_core.get('shock', {}).get('state', 'normal'))
    execution_state = {
        'mode': 'Long Now' if execution_score >= 0.58 and liquidity_fragility < 0.55 else ('Wait Reclaim' if risk_mode in {'stress', 'shock'} or execution_score < 0.48 else 'Add on Reset'),
        'score': execution_score,
    }

    return {
        'prices': prices,
        'flow': flow,
        'usage': usage,
        'supply_tightness': supply_tightness,
        'supply_overhang': supply_overhang,
        'leverage_heat': leverage_heat,
        'liquidity_fragility': liquidity_fragility,
        'holder_state': holder_state,
        'narrative': narrative,
        'trust_penalty': trust_penalty,
        'breadth_score': breadth_score,
        'execution_state': execution_state,
        'is_placeholder_heavy': len(leaders) < 8,
    }
