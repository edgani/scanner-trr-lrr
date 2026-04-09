from __future__ import annotations
from config.asset_buckets import COMMODITY_BUCKETS
from config.universe_registry import COMMODITIES_BACKEND_UNIVERSE, get_market_ranking_universe
from config.weights import COMMODITY_ENGINE_WEIGHTS
from utils.math_utils import clamp01
from utils.ranking_utils import rank_symbols, classify_action
from utils.ranking_context import commodity_ranking_context

FOCUS = {'GC=F','SI=F','CL=F','BZ=F'}


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


def run_commodity_native_engine(raw: dict, shared_core: dict, features: dict, macro_board: dict, transmission: dict) -> dict:
    prices=raw.get('prices', {})
    all_symbols = get_market_ranking_universe(COMMODITY_BUCKETS, COMMODITIES_BACKEND_UNIVERSE)
    ranking_ctx = commodity_ranking_context(shared_core, features)
    strong, weak = rank_symbols(prices, all_symbols, top_n=16, context=ranking_ctx)

    ctx = _regime_context(shared_core)
    breadth_snapshot = shared_core.get('breadth_snapshot', {}) or {}
    structural_map = {'Q1': 0.48, 'Q2': 0.66, 'Q3': 0.78, 'Q4': 0.54}
    monthly_map = {'Q1': 0.46, 'Q2': 0.62, 'Q3': 0.82, 'Q4': 0.50}
    structural_score, monthly_score, regime_score, divergence_gap = _blend_regime_score(
        ctx['structural_quad'], ctx['monthly_quad'], ctx['structural_conf'], ctx['monthly_conf'], ctx['dominant_horizon'], ctx['divergence'], structural_map, monthly_map
    )

    native = clamp01(0.26*features.get('physical_balance',0.5)+0.20*features.get('inventory_stress',0.5)+0.18*features.get('curve_tightness',0.5)+0.12*(1-features.get('positioning_vol',0.4))+0.14*(1-features.get('usd_rates_pressure',0.4))+0.10*features.get('exogenous_shock',0.4))
    family_strength = clamp01(0.45 * features.get('energy_strength', 0.5) + 0.35 * features.get('precious_strength', 0.5) + 0.20 * (1 - features.get('usd_rates_pressure', 0.5)))
    execution_score = float(features.get('execution_state', {}).get('score', 0.5) or 0.5)
    petrodollar_score = clamp01(0.45 * transmission.get('petrodollar_score', 0.5) + 0.30 * transmission.get('energy_dollar_feedback', 0.5) + 0.25 * features.get('exogenous_shock', 0.4))

    final_score = clamp01(
        COMMODITY_ENGINE_WEIGHTS['regime'] * regime_score
        + COMMODITY_ENGINE_WEIGHTS['native'] * native
        + COMMODITY_ENGINE_WEIGHTS['family_strength'] * family_strength
        + COMMODITY_ENGINE_WEIGHTS['execution'] * execution_score
        + COMMODITY_ENGINE_WEIGHTS['petrodollar'] * petrodollar_score
    )

    focus_longs = [r for r in strong if r['symbol'] in FOCUS][:4]
    focus_shorts = [r for r in weak if r['symbol'] in FOCUS][:4]
    extra_longs = [r for r in strong if r['symbol'] not in FOCUS][:3]
    extra_shorts = [r for r in weak if r['symbol'] not in FOCUS][:3]

    setups_now=[_setup_row(r,'long') for r in focus_longs + extra_longs] + [_setup_row(r,'short') for r in focus_shorts + extra_shorts]
    forward=[_radar_row(r,'long') for r in strong[4:8]] + [_radar_row(r,'short') for r in weak[4:8]]

    bucket_scores={}
    for bucket, syms in COMMODITY_BUCKETS.items():
        best, _ = rank_symbols(prices, syms, top_n=1, context=ranking_ctx)
        bucket_scores[bucket] = best[0]['score'] if best else 0.0

    chain={
        'XAU/USD':['NEM','GOLD','AEM','KGC','WPM','FNV','RGLD','GDX','GDXJ'],
        'XAG/USD':['PAAS','HL','AG','SILV','SIL','SILJ','FCX','SCCO','TECK'],
        'WTI/USD':['XOM','CVX','COP','SLB','HAL','BKR','OXY','DVN','EOG','STNG','FRO','TNK','DHT','KMI','WMB','OKE']
    }

    if transmission.get('petrodollar_state') == 'elevated':
        mode = 'Petrodollar / hard-asset tactical long'
    elif ctx['structural_quad'] == 'Q4' and ctx['monthly_quad'] == 'Q3':
        mode = 'Selective gold/energy, avoid broad cyclical chase'
    elif final_score > 0.60:
        mode = 'Long Now'
    else:
        mode = 'Wait Reset / two-way'

    return {
        'macro_vs_market':{**macro_board,'score':final_score,'structural_quad': ctx['structural_quad'], 'monthly_quad': ctx['monthly_quad'], 'operating_regime': ctx['operating_regime'], 'resolved_language': shared_core.get('resolved_regime', {}).get('resolved_language', ctx['operating_regime']), 'breadth_state': breadth_snapshot.get('breadth_state', '-'), 'breadth_score': breadth_snapshot.get('breadth_score', 0.5), 'narrow_leadership': breadth_snapshot.get('narrow_leadership', 0.5)},
        'transmission':transmission,
        'asset_checklist':macro_board.get('checklist',[]),
        'setups_now':setups_now[:12],
        'forward_radar':forward[:10],
        'market_hub':{
            'bucket_scores':dict(sorted(bucket_scores.items(), key=lambda kv: kv[1], reverse=True)),
            'execution_focus':[r['name'] for r in focus_longs + focus_shorts],
            'chain_beneficiaries':chain,
            'structural_quad': ctx['structural_quad'],
            'monthly_quad': ctx['monthly_quad'],
            'operating_regime': ctx['operating_regime'],
            'dominant_horizon': ctx['dominant_horizon'],
            'ranking_universe_size': len(all_symbols),
            'bucket_universe_size': sum(len(v) for v in COMMODITY_BUCKETS.values()),
            'breadth_state': breadth_snapshot.get('breadth_state', '-'),
            'breadth_score': breadth_snapshot.get('breadth_score', 0.5),
            'sector_support_ratio': breadth_snapshot.get('sector_support_ratio', 0.5),
            'narrow_leadership': breadth_snapshot.get('narrow_leadership', 0.5),
            'petrodollar_state': transmission.get('petrodollar_state', 'normal'),
            'structural_score': round(structural_score, 3),
            'monthly_score': round(monthly_score, 3),
            'dominant_horizon': ctx['dominant_horizon'],
            'ranking_universe_size': len(all_symbols),
            'bucket_universe_size': sum(len(v) for v in COMMODITY_BUCKETS.values()),
        },
        'strong_weak':{'strong_families':sorted(bucket_scores,key=bucket_scores.get,reverse=True)[:4],'weak_families':sorted(bucket_scores,key=bucket_scores.get)[:4],'strong_names':[r['name'] for r in strong[:8]],'weak_names':[r['name'] for r in weak[:8]]},
        'execution':{'bias':'Two-Way','mode':mode,'score':final_score,'notes':[
            f"Structural {ctx['structural_quad']} sets family preference; Monthly {ctx['monthly_quad']} decides whether the pulse is broad or tactical.",
            f"Petrodollar state: {transmission.get('petrodollar_state', 'normal')} with score {transmission.get('petrodollar_score', 0.5):.2f}.",
            f"Divergence gap {divergence_gap:.2f}; hard assets vs cyclicals should be separated explicitly.",
        ]}
    }


def _setup_row(r, side: str):
    return {'name':r['name'],'bucket':'Commodities','side':side,'score':round(r['score'],3),'why_now':f"r21 {r['r21']:.1%} · r63 {r['r63']:.1%} · eff {r['efficiency']:.2f} · ctx {r['context_adj']:.2f}",'action':classify_action(r['score'], side),'invalidator':'USD spike / curve lemah','risk':'High' if r['exhaustion'] > 0.55 else 'Medium','setup_type':'Execution Focus' if r['symbol'] in FOCUS else ('Family Leader' if side=='long' else 'Family Weakness')}


def _radar_row(r, side: str):
    return {'name':r['name'],'bucket':'Commodities','side':side,'score':round(r['score'],3),'why_radar':f"trend {r['trend']:.2f} · eff {r['efficiency']:.2f} · base {r['base_score']:.2f}",'not_ready':'tunggu curve / inventory confirm','trigger':'prompt spread / family breadth','risk':'Crowded' if side=='long' else 'Rebound risk','radar_type':'Almost Ready' if side=='long' else 'Short Radar'}
