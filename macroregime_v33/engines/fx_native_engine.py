from __future__ import annotations
from config.asset_buckets import FX_BUCKETS
from config.universe_registry import FX_BACKEND_UNIVERSE, get_market_ranking_universe
from config.weights import FX_ENGINE_WEIGHTS
from utils.math_utils import clamp01
from utils.ranking_utils import rank_symbols, classify_action
from utils.setup_utils import action_from_row, entry_zone_from_row, invalidation_from_row, target_summary_from_row, why_now_from_row, why_radar_from_row, not_ready_from_row, trigger_from_row, signal_quality_label, risk_label
from utils.ranking_context import fx_ranking_context


def _regime_context(shared_core: dict) -> dict:
    regime_stack = shared_core.get("regime_stack", {}) or {}
    resolved = regime_stack.get("resolved", {}) or {}
    structural_quad = regime_stack.get("structural", {}).get("quad", shared_core.get("regime", {}).get("current_quad", "Q?"))
    monthly_quad = regime_stack.get("monthly", {}).get("quad", structural_quad)
    dominant_horizon = resolved.get("dominant_horizon", "aligned")
    divergence = resolved.get("divergence_state", "aligned")
    operating = resolved.get("operating_regime", f"Monthly {monthly_quad} inside Structural {structural_quad}" if monthly_quad != structural_quad else f"Aligned {structural_quad}")
    structural_conf = float(regime_stack.get("structural", {}).get("confidence", shared_core.get("status_ribbon", {}).get("confidence", 0.5)) or 0.5)
    monthly_conf = float(regime_stack.get("monthly", {}).get("confidence", structural_conf) or structural_conf)
    return {
        "structural_quad": structural_quad,
        "monthly_quad": monthly_quad,
        "dominant_horizon": dominant_horizon,
        "divergence": divergence,
        "operating_regime": operating,
        "structural_conf": structural_conf,
        "monthly_conf": monthly_conf,
    }


def _blend_regime_score(structural_quad: str, monthly_quad: str, structural_conf: float, monthly_conf: float, dominant_horizon: str, divergence: str, structural_map: dict, monthly_map: dict) -> tuple[float, float, float, float]:
    structural_score = 0.60 * structural_map.get(structural_quad, 0.5) + 0.40 * structural_conf
    monthly_score = 0.60 * monthly_map.get(monthly_quad, 0.5) + 0.40 * monthly_conf
    if divergence == "aligned":
        regime_score = 0.70 * structural_score + 0.30 * monthly_score
    elif dominant_horizon == "monthly":
        regime_score = 0.40 * structural_score + 0.60 * monthly_score
    elif dominant_horizon == "structural":
        regime_score = 0.75 * structural_score + 0.25 * monthly_score
    else:
        regime_score = 0.55 * structural_score + 0.45 * monthly_score
    return structural_score, monthly_score, regime_score, abs(monthly_score - structural_score)


def run_fx_native_engine(raw: dict, shared_core: dict, features: dict, macro_board: dict, transmission: dict) -> dict:
    prices = raw.get('prices', {})
    price_frames = raw.get('price_frames', {})
    asset_ranges = (shared_core.get('risk_range', {}) or {}).get('asset_ranges', {}) or {}
    all_symbols = (raw.get('runtime_universe', {}) or {}).get('fx') or get_market_ranking_universe(FX_BUCKETS, FX_BACKEND_UNIVERSE)
    exec_flags = (shared_core.get('execution_mode', {}) or {}).get('flags', {}) or {}
    ranking_ctx = fx_ranking_context(shared_core, features)
    strong, weak = rank_symbols(prices, all_symbols, top_n=14, context=ranking_ctx, price_frames=price_frames, asset_ranges=asset_ranges)

    ctx = _regime_context(shared_core)
    breadth_snapshot = shared_core.get('breadth_snapshot', {}) or {}
    structural_map = {'Q1': 0.50, 'Q2': 0.56, 'Q3': 0.62, 'Q4': 0.68}
    monthly_map = {'Q1': 0.48, 'Q2': 0.54, 'Q3': 0.64, 'Q4': 0.66}
    structural_score, monthly_score, regime_score, divergence_gap = _blend_regime_score(
        ctx['structural_quad'], ctx['monthly_quad'], ctx['structural_conf'], ctx['monthly_conf'], ctx['dominant_horizon'], ctx['divergence'], structural_map, monthly_map
    )

    direction = clamp01(0.30*features.get('rate_diff',0.5)+0.20*features.get('real_rate_diff',0.5)+0.18*features.get('macro_surprise_diff',0.5)+0.17*features.get('external_balance_tot',0.5)+0.15*(1-features.get('intervention_risk',0.4)))
    amplifier = clamp01(0.40*(1-features.get('positioning_heat',0.4))+0.30*(1-features.get('options_heat',0.4))+0.30*features.get('liquidity_quality',0.6))
    pair_breadth = clamp01(features.get('pair_breadth', 0.5))
    execution_score = float(features.get('execution_state', {}).get('score', 0.45) or 0.45)

    final_score = clamp01(
        FX_ENGINE_WEIGHTS['regime'] * regime_score
        + FX_ENGINE_WEIGHTS['macro_direction'] * direction
        + FX_ENGINE_WEIGHTS['amplifier'] * amplifier
        + FX_ENGINE_WEIGHTS['pair_breadth'] * pair_breadth
        + FX_ENGINE_WEIGHTS['execution'] * execution_score
    )

    setups_now=[_setup_row(r,'long') for r in strong[:5]] + [_setup_row(r,'short') for r in weak[:5]]
    forward=[_radar_row(r,'long') for r in strong[5:8]] + [_radar_row(r,'short') for r in weak[5:8]]

    bucket_scores={}
    for bucket, syms in FX_BUCKETS.items():
        best, _ = rank_symbols(prices, syms, top_n=1, context=ranking_ctx, price_frames=price_frames, asset_ranges=asset_ranges)
        bucket_scores[bucket] = best[0]['score'] if best else 0.0

    if ctx['monthly_quad'] == 'Q3' and ctx['dominant_horizon'] == 'monthly':
        mode = 'Rates / importer pain pairs now'
    elif ctx['structural_quad'] == 'Q4':
        mode = 'Dollar / funding stress expressions'
    elif final_score > 0.58:
        mode = 'Long/short clean divergences now'
    else:
        mode = 'Wait cleaner repricing'

    return {
        'macro_vs_market':{**macro_board,'score':final_score,'structural_quad': ctx['structural_quad'], 'monthly_quad': ctx['monthly_quad'], 'operating_regime': ctx['operating_regime'], 'resolved_language': shared_core.get('resolved_regime', {}).get('resolved_language', ctx['operating_regime']), 'breadth_state': breadth_snapshot.get('breadth_state', '-'), 'breadth_score': breadth_snapshot.get('breadth_score', 0.5), 'narrow_leadership': breadth_snapshot.get('narrow_leadership', 0.5)},
        'transmission':transmission,
        'asset_checklist':macro_board.get('checklist',[]),
        'setups_now':setups_now,
        'forward_radar':forward,
        'market_hub':{
            'bucket_scores':dict(sorted(bucket_scores.items(), key=lambda kv: kv[1], reverse=True)),
            'intervention_risk':features.get('intervention_risk'),
            'options_heat':features.get('options_heat'),
            'positioning_heat':features.get('positioning_heat'),
            'structural_quad': ctx['structural_quad'],
            'monthly_quad': ctx['monthly_quad'],
            'operating_regime': ctx['operating_regime'],
            'dominant_horizon': ctx['dominant_horizon'],
            'ranking_universe_size': len(all_symbols),
            'bucket_universe_size': sum(len(v) for v in FX_BUCKETS.values()),
            'breadth_state': breadth_snapshot.get('breadth_state', '-'),
            'breadth_score': breadth_snapshot.get('breadth_score', 0.5),
            'sector_support_ratio': breadth_snapshot.get('sector_support_ratio', 0.5),
            'narrow_leadership': breadth_snapshot.get('narrow_leadership', 0.5),
            'structural_score': round(structural_score, 3),
            'monthly_score': round(monthly_score, 3),
            'dominant_horizon': ctx['dominant_horizon'],
            'ranking_universe_size': len(all_symbols),
            'bucket_universe_size': sum(len(v) for v in FX_BUCKETS.values()),
        },
        'strong_weak':{'strong_currencies':sorted(bucket_scores,key=bucket_scores.get,reverse=True)[:3],'weak_currencies':sorted(bucket_scores,key=bucket_scores.get)[:3],'strong_pairs':[r['name'] for r in strong[:8]],'weak_pairs':[r['name'] for r in weak[:8]]},
        'execution':{'bias':'Two-Way','mode':mode,'score':final_score,'notes':[
            f"Structural {ctx['structural_quad']} defines core DXY/funding backdrop.",
            f"Monthly {ctx['monthly_quad']} decides whether carry, importer pain, or relief pairs are the cleanest tactical expression.",
            f"Divergence gap {divergence_gap:.2f}; intervention risk stays central in FX.",
        ]}
    }


def _setup_row(r, side: str):
    base_action = classify_action(r['score'], side)
    return {
        'name': r['name'],
        'bucket': 'FX',
        'side': side,
        'score': round(r['score'], 3),
        'why_now': why_now_from_row(r, side),
        'entry_zone': entry_zone_from_row(r, side, is_radar=False),
        't1_t2': target_summary_from_row(r, side, is_radar=False),
        'signal_quality': signal_quality_label(r),
        'action': action_from_row(r, side, base_action),
        'invalidator': invalidation_from_row(r, side, 'macro surprise berbalik / intervention'),
        'risk': risk_label(r, side, high_vol=0.05),
        'setup_type': 'Clean Divergence' if side == 'long' else 'Weak / Fragile Pair',
        'target': target_summary_from_row(r, side, is_radar=False),
    }


def _radar_row(r, side: str):
    why_not = not_ready_from_row(r, side)
    return {
        'name': r['name'],
        'bucket': 'FX',
        'side': side,
        'score': round(r['score'], 3),
        'why_radar': why_radar_from_row(r, side),
        'entry_zone': entry_zone_from_row(r, side, is_radar=True),
        't1_t2': target_summary_from_row(r, side, is_radar=True),
        'why_not_yet': why_not,
        'not_ready': why_not,
        'trigger': trigger_from_row(r, side),
        'signal_quality': signal_quality_label(r),
        'risk': 'Whipsaw',
        'radar_type': 'Almost Ready' if side == 'long' else 'Short Radar',
        'target': target_summary_from_row(r, side, is_radar=True),
    }
