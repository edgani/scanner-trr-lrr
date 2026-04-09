from __future__ import annotations
from config.asset_buckets import IHSG_BUCKETS
from config.universe_registry import IHSG_BACKEND_UNIVERSE, get_market_ranking_universe
from config.weights import IHSG_ENGINE_WEIGHTS
from utils.math_utils import clamp01
from utils.ranking_utils import rank_symbols, classify_action, classify_radar
from utils.setup_utils import action_from_row, entry_zone_from_row, invalidation_from_row, target_summary_from_row, why_now_from_row, why_radar_from_row, not_ready_from_row, trigger_from_row, signal_quality_label, risk_label
from utils.ranking_context import ihsg_ranking_context


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


def run_ihsg_native_engine(raw: dict, shared_core: dict, features: dict, macro_board: dict, transmission: dict) -> dict:
    prices = raw.get('prices', {})
    price_frames = raw.get('price_frames', {})
    asset_ranges = (shared_core.get('risk_range', {}) or {}).get('asset_ranges', {}) or {}
    all_symbols = (raw.get('runtime_universe', {}) or {}).get('ihsg') or get_market_ranking_universe(IHSG_BUCKETS, IHSG_BACKEND_UNIVERSE)
    exec_flags = (shared_core.get('execution_mode', {}) or {}).get('flags', {}) or {}
    ranking_ctx = ihsg_ranking_context(shared_core, features)
    strong, weak = rank_symbols(prices, all_symbols, top_n=16, context=ranking_ctx, price_frames=price_frames, asset_ranges=asset_ranges)

    ctx = _regime_context(shared_core)
    breadth_snapshot = shared_core.get('breadth_snapshot', {}) or {}
    emr = shared_core.get('em_rotation', {}) or {}
    structural_map = {'Q1': 0.60, 'Q2': 0.68, 'Q3': 0.58, 'Q4': 0.38}
    monthly_map = {'Q1': 0.56, 'Q2': 0.66, 'Q3': 0.66, 'Q4': 0.34}
    structural_score, monthly_score, regime_score, divergence_gap = _blend_regime_score(
        ctx['structural_quad'], ctx['monthly_quad'], ctx['structural_conf'], ctx['monthly_conf'], ctx['dominant_horizon'], ctx['divergence'], structural_map, monthly_map
    )

    native_score = clamp01(
        0.20 * features.get('global_risk', 0.5)
        + 0.14 * (1 - features.get('usd_idr_pressure', 0.5))
        + 0.18 * features.get('foreign_flow', 0.5)
        + 0.14 * features.get('breadth_liquidity', 0.5)
        + 0.14 * features.get('bank_health', 0.5)
        + 0.10 * features.get('heavyweights', 0.5)
        + 0.10 * features.get('commodity_spillover', 0.5)
    )
    breadth_flow = clamp01(0.55 * features.get('breadth_liquidity', 0.5) + 0.45 * features.get('foreign_flow', 0.5))
    em_score = float(emr.get('resolved_score', emr.get('score', 0.4)) or 0.4)
    execution_score = float(features.get('execution_state', {}).get('score', 0.45) or 0.45)

    final_score = clamp01(
        IHSG_ENGINE_WEIGHTS['regime'] * regime_score
        + IHSG_ENGINE_WEIGHTS['em_rotation'] * em_score
        + IHSG_ENGINE_WEIGHTS['macro_native'] * native_score
        + IHSG_ENGINE_WEIGHTS['breadth_flow'] * breadth_flow
        + IHSG_ENGINE_WEIGHTS['execution'] * execution_score
    )

    long_rows = [_setup_row(r, 'long') for r in strong[:6]]
    short_rows = [_setup_row(r, 'short') for r in weak[:6]]
    setups_now = long_rows + short_rows
    forward = [_radar_row(r, 'long') for r in strong[6:10]] + [_radar_row(r, 'short') for r in weak[6:10]]

    bucket_scores = {}
    for bucket, syms in IHSG_BUCKETS.items():
        ranked_strong, _ = rank_symbols(prices, syms, top_n=1, context=ranking_ctx, price_frames=price_frames, asset_ranges=asset_ranges)
        bucket_scores[bucket] = ranked_strong[0]['score'] if ranked_strong else 0.0

    if ctx['dominant_horizon'] == 'monthly' and ctx['monthly_quad'] == 'Q3':
        mode = 'Tactical exporter / resource long on reset'
    elif ctx['structural_quad'] == 'Q4' and ctx['dominant_horizon'] == 'structural':
        mode = 'Selective defensives / banks only'
    elif final_score > 0.58:
        mode = 'Add on Reset'
    elif final_score > 0.46:
        mode = 'Wait Reclaim'
    else:
        mode = 'Defensive / selective only'

    return {
        'macro_vs_market': {**macro_board, 'score': final_score, 'structural_quad': ctx['structural_quad'], 'monthly_quad': ctx['monthly_quad'], 'operating_regime': ctx['operating_regime'], 'resolved_language': shared_core.get('resolved_regime', {}).get('resolved_language', ctx['operating_regime']), 'breadth_state': breadth_snapshot.get('breadth_state', '-'), 'breadth_score': breadth_snapshot.get('breadth_score', 0.5), 'narrow_leadership': breadth_snapshot.get('narrow_leadership', 0.5)},
        'transmission': transmission,
        'asset_checklist': macro_board.get('checklist', []),
        'setups_now': setups_now,
        'forward_radar': forward,
        'market_hub': {
            'foreign_flow_score': features.get('foreign_flow'),
            'usd_idr_pressure': features.get('usd_idr_pressure'),
            'indo_yield_pressure': features.get('indo_yield_pressure'),
            'bank_health': features.get('bank_health'),
            'commodity_spillover': features.get('commodity_spillover'),
            'clean_float_rotation_score': features.get('clean_float_rotation_score', 0.0),
            'structural_registry_coverage': (features.get('structural_state', {}) or {}).get('registry_coverage', 0),
            'bucket_scores': bucket_scores,
            'structural_quad': ctx['structural_quad'],
            'monthly_quad': ctx['monthly_quad'],
            'operating_regime': ctx['operating_regime'],
            'dominant_horizon': ctx['dominant_horizon'],
            'breadth_state': breadth_snapshot.get('breadth_state', '-'),
            'breadth_score': breadth_snapshot.get('breadth_score', 0.5),
            'sector_support_ratio': breadth_snapshot.get('sector_support_ratio', 0.5),
            'narrow_leadership': breadth_snapshot.get('narrow_leadership', 0.5),
            'structural_score': round(structural_score, 3),
            'monthly_score': round(monthly_score, 3),
            'dominant_horizon': ctx['dominant_horizon'],
            'resolved_em_rotation': emr.get('resolved_state', emr.get('state', 'selective')),
            'ranking_universe_size': len(all_symbols),
            'bucket_universe_size': sum(len(v) for v in IHSG_BUCKETS.values()),
        },
        'strong_weak': {
            'strong_sectors': sorted(bucket_scores, key=bucket_scores.get, reverse=True)[:4],
            'weak_sectors': sorted(bucket_scores, key=bucket_scores.get)[:4],
            'strong_names': [r['name'] for r in strong[:8]],
            'weak_names': [r['name'] for r in weak[:8]],
        },
        'execution': {'flags': exec_flags, 
            'bias': 'Two-Way Diagnostic',
            'mode': mode,
            'score': final_score,
            'notes': [
                f"Structural {ctx['structural_quad']} decides whether IHSG should be treated as backdrop-friendly or backdrop-fragile.",
                f"Monthly {ctx['monthly_quad']} decides whether exporters/banks can still lead tactically.",
                f"EM rotation resolved state: {emr.get('resolved_state', emr.get('state', 'selective'))}; divergence gap {divergence_gap:.2f}.",
            ],
        },
    }


def _setup_row(r, side):
    leaders = {'BBCA.JK', 'BBRI.JK', 'BMRI.JK', 'ADRO.JK', 'PTBA.JK', 'ITMG.JK', 'AADI.JK', 'ANTM.JK', 'MDKA.JK'}
    struct_flag = str(r.get('structural_flag', '') or '')
    base_action = classify_action(r['score'], side=side)
    return {
        'name': r['name'],
        'bucket': 'IHSG',
        'side': side,
        'score': round(r['score'], 3),
        'why_now': why_now_from_row(r, side),
        'entry_zone': entry_zone_from_row(r, side, is_radar=False),
        't1_t2': target_summary_from_row(r, side, is_radar=False),
        'signal_quality': signal_quality_label(r),
        'action': action_from_row(r, side, base_action),
        'invalidator': invalidation_from_row(r, side, 'USD/IDR naik lagi / breadth rusak' if side == 'long' else 'breadth recover / foreign sell reda'),
        'risk': risk_label(r, side, high_vol=0.05),
        'microstructure_flag': struct_flag,
        'setup_type': ('Banks/Resources Leader' if side == 'long' and r['symbol'] in leaders else ('Vulnerable Laggard' if side == 'short' else 'Selective Leader')),
        'target': target_summary_from_row(r, side, is_radar=False),
    }


def _radar_row(r, side):
    struct_flag = str(r.get('structural_flag', '') or '')
    why_not = not_ready_from_row(r, side)
    return {
        'name': r['name'],
        'bucket': 'IHSG',
        'side': side,
        'score': round(r['score'], 3),
        'why_radar': why_radar_from_row(r, side),
        'entry_zone': entry_zone_from_row(r, side, is_radar=True),
        't1_t2': target_summary_from_row(r, side, is_radar=True),
        'why_not_yet': why_not,
        'not_ready': why_not,
        'trigger': trigger_from_row(r, side),
        'signal_quality': signal_quality_label(r),
        'risk': 'High' if r['vol21'] > 0.05 or r['exhaustion'] > 0.50 else 'Normal',
        'microstructure_flag': struct_flag,
        'radar_type': classify_radar(r['score'] if side == 'long' else -abs(r['score'])),
        'target': target_summary_from_row(r, side, is_radar=True),
    }
