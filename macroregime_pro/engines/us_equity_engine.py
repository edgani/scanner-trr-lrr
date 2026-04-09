from __future__ import annotations
from config.asset_buckets import US_BUCKETS
from config.universe_registry import US_BACKEND_UNIVERSE, get_market_ranking_universe
from config.weights import US_ENGINE_WEIGHTS
from utils.ranking_utils import rank_symbols, classify_action, classify_radar
from utils.ranking_context import us_ranking_context


def run_us_equity_engine(raw: dict, shared_core: dict, features: dict, macro_board: dict, transmission: dict) -> dict:
    prices = raw.get('prices', {})
    all_symbols = get_market_ranking_universe(US_BUCKETS, US_BACKEND_UNIVERSE)
    ranking_ctx = us_ranking_context(shared_core, features)
    strong, weak = rank_symbols(prices, all_symbols, top_n=16, context=ranking_ctx)

    long_rows = [_setup_row(r, 'US', 'long') for r in strong[:6]]
    short_rows = [_setup_row(r, 'US', 'short') for r in weak[:6]]
    setups_now = long_rows + short_rows

    long_forward = [_radar_row(r, 'US', 'long') for r in strong[6:10]]
    short_forward = [_radar_row(r, 'US', 'short') for r in weak[6:10]]
    forward = long_forward + short_forward

    sector_scores = {}
    for bucket, syms in US_BUCKETS.items():
        ranked_strong, _ = rank_symbols(prices, syms, top_n=2, context=ranking_ctx)
        sector_scores[bucket] = sum(r['score'] for r in ranked_strong) / len(ranked_strong) if ranked_strong else 0.0

    strong_buckets = sorted(sector_scores, key=sector_scores.get, reverse=True)[:4]
    weak_buckets = sorted(sector_scores, key=sector_scores.get)[:4]

    regime_stack = shared_core.get('regime_stack', {}) or {}
    structural_quad = regime_stack.get('structural', {}).get('quad', shared_core.get('regime', {}).get('current_quad', 'Q3'))
    monthly_quad = regime_stack.get('monthly', {}).get('quad', structural_quad)
    divergence = regime_stack.get('resolved', {}).get('divergence_state', 'aligned')
    dominant_horizon = regime_stack.get('resolved', {}).get('dominant_horizon', 'aligned')

    structural_map = {'Q1': 0.72, 'Q2': 0.80, 'Q3': 0.52, 'Q4': 0.28}
    monthly_map = {'Q1': 0.68, 'Q2': 0.76, 'Q3': 0.48, 'Q4': 0.30}

    structural_conf = regime_stack.get('structural', {}).get('confidence', shared_core.get('status_ribbon', {}).get('confidence', 0.5))
    monthly_conf = regime_stack.get('monthly', {}).get('confidence', structural_conf)

    structural_score = 0.60 * structural_map.get(structural_quad, 0.5) + 0.40 * float(structural_conf)
    monthly_score = 0.60 * monthly_map.get(monthly_quad, 0.5) + 0.40 * float(monthly_conf)

    if divergence == 'aligned':
        regime_score = 0.70 * structural_score + 0.30 * monthly_score
    elif dominant_horizon == 'monthly':
        regime_score = 0.40 * structural_score + 0.60 * monthly_score
    elif dominant_horizon == 'structural':
        regime_score = 0.75 * structural_score + 0.25 * monthly_score
    else:
        regime_score = 0.55 * structural_score + 0.45 * monthly_score

    breadth_credit_vol = (features.get('breadth_health', 0.5) + features.get('credit_ok', 0.5) + features.get('vol_ok', 0.5)) / 3.0
    sector_style_score = max(sector_scores.values()) if sector_scores else 0.5
    stock_ranking_score = strong[0]['score'] if strong else 0.0
    execution_score = features.get('execution_state', {}).get('score', shared_core.get('execution_mode', {}).get('score', 0.5))

    final_score = (
        US_ENGINE_WEIGHTS['regime'] * regime_score
        + US_ENGINE_WEIGHTS['breadth_credit_vol'] * breadth_credit_vol
        + US_ENGINE_WEIGHTS['sector_style'] * sector_style_score
        + US_ENGINE_WEIGHTS['stock_ranking'] * stock_ranking_score
        + US_ENGINE_WEIGHTS['execution'] * execution_score
    )

    crash_state = shared_core.get('risk_summary', {}).get('crash_state', 'calm')
    if crash_state == 'elevated':
        mode = 'Defensive / wait for reclaim'
    elif dominant_horizon == 'monthly' and divergence == 'divergent' and final_score > 0.10:
        mode = 'Tactical Long on Reset'
    elif final_score > 0.16:
        mode = 'Long on Reset'
    elif final_score > 0.08:
        mode = 'Wait Long Reclaim'
    else:
        mode = 'Selective / two-way'

    return {
        'macro_vs_market': {**macro_board, 'score': final_score, 'structural_quad': structural_quad, 'monthly_quad': monthly_quad, 'operating_regime': regime_stack.get('resolved', {}).get('operating_regime', '-')},
        'transmission': transmission,
        'asset_checklist': macro_board.get('checklist', []),
        'setups_now': setups_now,
        'forward_radar': forward,
        'market_hub': {
            'sector_scores': sector_scores,
            'mag7_concentration': features.get('mag7_concentration'),
            'breadth_notes': 'Structural quad drives backbone sector/style map; monthly quad decides whether the move is tactical, broadening, or fading.',
            'risk_range_state': shared_core.get('risk_range', {}).get('range_state', 'normal'),
            'structural_quad': structural_quad,
            'monthly_quad': monthly_quad,
            'operating_regime': regime_stack.get('resolved', {}).get('operating_regime', '-'),
            'dominant_horizon': dominant_horizon,
            'ranking_universe_size': len(all_symbols),
            'bucket_universe_size': sum(len(v) for v in US_BUCKETS.values()),
        },
        'strong_weak': {
            'strong_sectors': strong_buckets,
            'weak_sectors': weak_buckets,
            'strong_names': [r['name'] for r in strong[:8]],
            'weak_names': [r['name'] for r in weak[:8]],
        },
        'execution': {
            'bias': 'Two-Way' if divergence == 'divergent' else ('Risk-On' if monthly_quad in {'Q1','Q2'} else 'Defensive'),
            'mode': mode,
            'score': final_score,
            'notes': [
                f'Structural {structural_quad} gives backbone sector/style bias.',
                f'Monthly {monthly_quad} with dominant horizon {dominant_horizon} decides whether to chase, wait, or fade.',
                'Long pakai breadth/rotation confirm, short pakai weak breadth + crowding failure.',
            ],
        },
    }


def _setup_row(r, bucket, side):
    return {
        'name': r['name'],
        'bucket': bucket,
        'side': side,
        'score': round(r['score'], 3),
        'why_now': f"r21 {r['r21']:.1%} · r63 {r['r63']:.1%} · eff {r['efficiency']:.2f} · base {r['base_score']:.2f} ctx {r['context_adj']:.2f}",
        'action': classify_action(r['score'], side=side),
        'invalidator': 'breadth gagal confirm / yield spike' if side == 'long' else 'breadth recover / squeeze risk',
        'risk': 'High' if r['vol21'] > 0.05 or r['exhaustion'] > 0.55 else 'Medium',
        'setup_type': 'Clean Continuation' if side == 'long' and r['score'] > 0.16 and r['exhaustion'] < 0.50 else ('Weak Breakdown' if side == 'short' else 'Early Rotation'),
    }


def _radar_row(r, bucket, side):
    return {
        'name': r['name'],
        'bucket': bucket,
        'side': side,
        'score': round(r['score'], 3),
        'why_radar': f"trend {r['trend']:.2f} · eff {r['efficiency']:.2f} · base {r['base_score']:.2f}",
        'not_ready': 'masih butuh breadth/price reset' if side == 'long' else 'masih butuh breakdown/failed bounce',
        'trigger': 'equal-weight / sector breadth ikut confirm' if side == 'long' else 'failed bounce + breadth tetap sempit',
        'risk': 'Crowded' if side == 'long' and (r['score'] > 0.18 or r['exhaustion'] > 0.55) else 'Normal',
        'radar_type': classify_radar(r['score'] if side == 'long' else -abs(r['score'])),
    }
