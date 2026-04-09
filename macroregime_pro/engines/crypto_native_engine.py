from __future__ import annotations
from config.asset_buckets import CRYPTO_BUCKETS
from config.universe_registry import CRYPTO_BACKEND_UNIVERSE, get_market_ranking_universe
from config.weights import CRYPTO_ENGINE_WEIGHTS
from utils.math_utils import clamp01
from utils.ranking_utils import rank_symbols, classify_action
from utils.ranking_context import crypto_ranking_context


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


def run_crypto_native_engine(raw: dict, shared_core: dict, features: dict, macro_board: dict, transmission: dict) -> dict:
    prices=raw.get('prices', {})
    all_symbols = get_market_ranking_universe(CRYPTO_BUCKETS, CRYPTO_BACKEND_UNIVERSE)
    ranking_ctx = crypto_ranking_context(shared_core, features)
    strong, weak = rank_symbols(prices, all_symbols, top_n=16, context=ranking_ctx)

    ctx = _regime_context(shared_core)
    breadth_snapshot = shared_core.get('breadth_snapshot', {}) or {}
    structural_map = {'Q1': 0.64, 'Q2': 0.78, 'Q3': 0.40, 'Q4': 0.24}
    monthly_map = {'Q1': 0.60, 'Q2': 0.74, 'Q3': 0.44, 'Q4': 0.22}
    structural_score, monthly_score, regime_score, divergence_gap = _blend_regime_score(
        ctx['structural_quad'], ctx['monthly_quad'], ctx['structural_conf'], ctx['monthly_conf'], ctx['dominant_horizon'], ctx['divergence'], structural_map, monthly_map
    )

    boom = clamp01(0.24*features.get('flow',0.5)+0.16*features.get('usage',0.5)+0.15*features.get('supply_tightness',0.5)+0.14*features.get('narrative',0.5)+0.11*features.get('holder_state',0.5)+0.10*(1-features.get('liquidity_fragility',0.4))+0.10*shared_core.get('status_ribbon',{}).get('confidence',0.5))
    fragility = clamp01(0.30*features.get('leverage_heat',0.4)+0.25*features.get('liquidity_fragility',0.4)+0.20*features.get('supply_overhang',0.3)+0.15*features.get('trust_penalty',0.2)+0.10*0.4)
    breadth_score = clamp01(features.get('breadth_score', 0.5))
    execution_score = float(features.get('execution_state', {}).get('score', 0.45) or 0.45)

    final_score = clamp01(
        CRYPTO_ENGINE_WEIGHTS['regime'] * regime_score
        + CRYPTO_ENGINE_WEIGHTS['boom'] * boom
        + CRYPTO_ENGINE_WEIGHTS['fragility_penalty'] * fragility
        + CRYPTO_ENGINE_WEIGHTS['breadth'] * breadth_score
        + CRYPTO_ENGINE_WEIGHTS['execution'] * execution_score
    )

    setups_now=[_setup_row(r,'long') for r in strong[:6]] + [_setup_row(r,'short') for r in weak[:6]]
    forward=[_radar_row(r,'long') for r in strong[6:10]] + [_radar_row(r,'short') for r in weak[6:10]]

    bucket_scores={}
    for bucket, syms in CRYPTO_BUCKETS.items():
        best, _ = rank_symbols(prices, syms, top_n=1, context=ranking_ctx)
        bucket_scores[bucket] = best[0]['score'] if best else 0.0

    if ctx['structural_quad'] in {'Q3','Q4'} and ctx['dominant_horizon'] == 'structural':
        mode = 'Majors only / tactical shorts on fragile beta'
    elif ctx['monthly_quad'] in {'Q1','Q2'} and final_score > 0.56:
        mode = 'Add on Reset / breadth-confirmed'
    else:
        mode = 'Wait Reset / tactical only'

    return {
        'macro_vs_market':{**macro_board,'score':final_score,'structural_quad': ctx['structural_quad'], 'monthly_quad': ctx['monthly_quad'], 'operating_regime': ctx['operating_regime'], 'resolved_language': shared_core.get('resolved_regime', {}).get('resolved_language', ctx['operating_regime']), 'breadth_state': breadth_snapshot.get('breadth_state', '-'), 'breadth_score': breadth_snapshot.get('breadth_score', 0.5), 'narrow_leadership': breadth_snapshot.get('narrow_leadership', 0.5)},
        'transmission':transmission,
        'asset_checklist':macro_board.get('checklist',[]),
        'setups_now':setups_now,
        'forward_radar':forward,
        'market_hub':{
            'bucket_scores':dict(sorted(bucket_scores.items(), key=lambda kv: kv[1], reverse=True)),
            'flow':features.get('flow'),
            'usage':features.get('usage'),
            'leverage_heat':features.get('leverage_heat'),
            'liquidity_fragility':features.get('liquidity_fragility'),
            'structural_quad': ctx['structural_quad'],
            'monthly_quad': ctx['monthly_quad'],
            'operating_regime': ctx['operating_regime'],
            'dominant_horizon': ctx['dominant_horizon'],
            'ranking_universe_size': len(all_symbols),
            'bucket_universe_size': sum(len(v) for v in CRYPTO_BUCKETS.values()),
            'breadth_state': breadth_snapshot.get('breadth_state', '-'),
            'breadth_score': breadth_snapshot.get('breadth_score', 0.5),
            'sector_support_ratio': breadth_snapshot.get('sector_support_ratio', 0.5),
            'narrow_leadership': breadth_snapshot.get('narrow_leadership', 0.5),
            'structural_score': round(structural_score, 3),
            'monthly_score': round(monthly_score, 3),
            'dominant_horizon': ctx['dominant_horizon'],
            'ranking_universe_size': len(all_symbols),
            'bucket_universe_size': sum(len(v) for v in CRYPTO_BUCKETS.values()),
        },
        'strong_weak':{'strong_sectors':sorted(bucket_scores,key=bucket_scores.get,reverse=True)[:4],'weak_sectors':sorted(bucket_scores,key=bucket_scores.get)[:4],'strong_tokens':[r['name'] for r in strong[:8]],'weak_tokens':[r['name'] for r in weak[:8]]},
        'execution':{'bias':'Two-Way','mode':mode,'score':final_score,'notes':[
            f"Structural {ctx['structural_quad']} sets global liquidity/beta backdrop.",
            f"Monthly {ctx['monthly_quad']} decides whether breadth can broaden beyond majors.",
            f"Divergence gap {divergence_gap:.2f}; fragility {fragility:.2f} vs boom {boom:.2f}.",
        ]}
    }


def _setup_row(r, side: str):
    return {'name':r['name'],'bucket':'Crypto','side':side,'score':round(r['score'],3),'why_now':f"r21 {r['r21']:.1%} · r63 {r['r63']:.1%} · eff {r['efficiency']:.2f} · ctx {r['context_adj']:.2f}",'action':classify_action(r['score'], side),'invalidator':'funding panas / exchange inflow naik','risk':'High' if r['vol21']>0.08 or r['exhaustion'] > 0.55 else 'Medium','setup_type':'Healthy Expansion' if side=='long' else 'Fragile / Distribution'}


def _radar_row(r, side: str):
    return {'name':r['name'],'bucket':'Crypto','side':side,'score':round(r['score'],3),'why_radar':f"trend {r['trend']:.2f} · eff {r['efficiency']:.2f} · base {r['base_score']:.2f}",'not_ready':'butuh breadth/flow confirm','trigger':'stablecoin flow + majors confirm','risk':'Fragile','radar_type':'Almost Ready' if side=='long' else 'Short Radar'}
