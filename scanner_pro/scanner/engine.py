from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import math
import pandas as pd
from config.settings import HOLDING_WINDOWS, MIN_HISTORY_BARS, RISK_REWARD_MIN
from .features import compute_features
from .history_store import history_status
from .macro_overlay import load_macro_snapshot, macro_alignment_for_side, macro_multiplier, market_macro_overlay
from .price_loader import load_market_histories, update_market_histories
from .snapshot_store import save_snapshot
from .universe_loader import load_universe

@dataclass
class ScanConfig:
    market: str
    force_refresh: bool = False
    use_cached_only: bool = True

def _pretty_bias(state: str, side: str, countertrend: bool = False) -> str:
    base = {
        'bullish': 'Bullish',
        'improving': 'Improving',
        'mixed': 'Mixed',
        'weakening': 'Weakening',
        'bearish': 'Bearish',
    }.get(state, state.title())
    if countertrend:
        return f'Countertrend {side}'
    return f'{base} {side}'

def _rr(entry: float, invalidation: float, target: float, side: str) -> float:
    if side == 'Long':
        reward = target - entry
        risk = entry - invalidation
    else:
        reward = entry - target
        risk = invalidation - entry
    if risk <= 0:
        return 0.0
    return max(0.0, reward / risk)

def _current_play(symbol: str, features: dict, overlay: dict) -> dict | None:
    close = features['last_close']
    atr = features['atr']
    long_align, long_mult, long_expl = macro_alignment_for_side('Long', overlay)
    short_align, short_mult, short_expl = macro_alignment_for_side('Short', overlay)

    short_state = features['short_state']
    mid_state = features['mid_state']
    long_state = features['long_state']

    candidates: list[dict] = []

    # Short-term continuation or tactical countertrend
    if short_state in {'bullish', 'improving'}:
        entry = max(features['trade_lrr'], close - 0.25 * atr)
        invalidation = features['trend_lrr']
        target = features['trade_trr']
        rr = _rr(entry, invalidation, target, 'Long')
        if rr >= RISK_REWARD_MIN['short_term']:
            candidates.append({
                'Ticker': symbol, 'horizon_bucket': 'short_term', 'long_or_short': 'Long', 'next_flag': 0,
                'Bias': _pretty_bias(short_state, 'Long'),
                'Entry Zone': f"{entry:.4f} - {min(entry + 0.35*atr, close + 0.25*atr):.4f}",
                'Invalidation': round(invalidation, 4),
                'Target': round(target, 4),
                'Holding Window': HOLDING_WINDOWS['short_term'],
                'Macro Aligned?': long_align,
                'macro_explanation': long_expl,
                'entry_mid': entry,
                'rr_score': round(rr, 2),
                'ev_score': round(rr * long_mult, 2),
                'route': overlay.get('next_route', '') or overlay.get('summary', ''),
                'why_now': 'Momentum pendek searah dan entry masih dekat range bawah.',
                'why_not_yet': '',
            })
    if short_state in {'bearish', 'weakening'}:
        entry = min(features['trade_trr'], close + 0.25 * atr)
        invalidation = features['trend_trr']
        target = features['trade_lrr']
        rr = _rr(entry, invalidation, target, 'Short')
        if rr >= RISK_REWARD_MIN['short_term']:
            candidates.append({
                'Ticker': symbol, 'horizon_bucket': 'short_term', 'long_or_short': 'Short', 'next_flag': 0,
                'Bias': _pretty_bias(short_state, 'Short'),
                'Entry Zone': f"{max(entry - 0.35*atr, close - 0.25*atr):.4f} - {entry:.4f}",
                'Invalidation': round(invalidation, 4),
                'Target': round(target, 4),
                'Holding Window': HOLDING_WINDOWS['short_term'],
                'Macro Aligned?': short_align,
                'macro_explanation': short_expl,
                'entry_mid': entry,
                'rr_score': round(rr, 2),
                'ev_score': round(rr * short_mult, 2),
                'route': overlay.get('next_route', '') or overlay.get('summary', ''),
                'why_now': 'Momentum pendek searah dan entry masih dekat range atas.',
                'why_not_yet': '',
            })

    # Mid-term continuation
    if mid_state in {'bullish', 'improving'} and features['dist_trade_low'] <= 2.0:
        entry = max(features['trend_lrr'], close - 0.35 * atr)
        invalidation = features['position_lrr']
        target = features['trend_trr']
        rr = _rr(entry, invalidation, target, 'Long')
        if rr >= RISK_REWARD_MIN['mid_term']:
            candidates.append({
                'Ticker': symbol, 'horizon_bucket': 'mid_term', 'long_or_short': 'Long', 'next_flag': 0,
                'Bias': _pretty_bias(mid_state, 'Long'),
                'Entry Zone': f"{entry:.4f} - {min(entry + 0.5*atr, close + 0.25*atr):.4f}",
                'Invalidation': round(invalidation, 4),
                'Target': round(target, 4),
                'Holding Window': HOLDING_WINDOWS['mid_term'],
                'Macro Aligned?': long_align,
                'macro_explanation': long_expl,
                'entry_mid': entry,
                'rr_score': round(rr, 2),
                'ev_score': round(rr * long_mult, 2),
                'route': overlay.get('next_route', '') or overlay.get('summary', ''),
                'why_now': 'Trend menengah searah dan harga belum terlalu jauh dari value/trend range.',
                'why_not_yet': '',
            })
    if mid_state in {'bearish', 'weakening'} and features['dist_trade_high'] <= 2.0:
        entry = min(features['trend_trr'], close + 0.35 * atr)
        invalidation = features['position_trr']
        target = features['trend_lrr']
        rr = _rr(entry, invalidation, target, 'Short')
        if rr >= RISK_REWARD_MIN['mid_term']:
            candidates.append({
                'Ticker': symbol, 'horizon_bucket': 'mid_term', 'long_or_short': 'Short', 'next_flag': 0,
                'Bias': _pretty_bias(mid_state, 'Short'),
                'Entry Zone': f"{max(entry - 0.5*atr, close - 0.25*atr):.4f} - {entry:.4f}",
                'Invalidation': round(invalidation, 4),
                'Target': round(target, 4),
                'Holding Window': HOLDING_WINDOWS['mid_term'],
                'Macro Aligned?': short_align,
                'macro_explanation': short_expl,
                'entry_mid': entry,
                'rr_score': round(rr, 2),
                'ev_score': round(rr * short_mult, 2),
                'route': overlay.get('next_route', '') or overlay.get('summary', ''),
                'why_now': 'Trend menengah turun dan area entry masih belum telat.',
                'why_not_yet': '',
            })

    # Long-term continuation
    if long_state in {'bullish', 'improving'} and close > features['ema200']:
        entry = max(features['position_lrr'], close - 0.5 * atr)
        invalidation = features['tail_lrr']
        target = features['position_trr']
        rr = _rr(entry, invalidation, target, 'Long')
        if rr >= RISK_REWARD_MIN['long_term']:
            candidates.append({
                'Ticker': symbol, 'horizon_bucket': 'long_term', 'long_or_short': 'Long', 'next_flag': 0,
                'Bias': _pretty_bias(long_state, 'Long'),
                'Entry Zone': f"{entry:.4f} - {min(entry + 0.75*atr, close + 0.35*atr):.4f}",
                'Invalidation': round(invalidation, 4),
                'Target': round(target, 4),
                'Holding Window': HOLDING_WINDOWS['long_term'],
                'Macro Aligned?': long_align,
                'macro_explanation': long_expl,
                'entry_mid': entry,
                'rr_score': round(rr, 2),
                'ev_score': round(rr * long_mult, 2),
                'route': overlay.get('next_route', '') or overlay.get('summary', ''),
                'why_now': 'Trend panjang masih hidup dan reward jangka lebih panjang masih cukup.',
                'why_not_yet': '',
            })
    if long_state in {'bearish', 'weakening'} and close < features['ema200']:
        entry = min(features['position_trr'], close + 0.5 * atr)
        invalidation = features['tail_trr']
        target = features['position_lrr']
        rr = _rr(entry, invalidation, target, 'Short')
        if rr >= RISK_REWARD_MIN['long_term']:
            candidates.append({
                'Ticker': symbol, 'horizon_bucket': 'long_term', 'long_or_short': 'Short', 'next_flag': 0,
                'Bias': _pretty_bias(long_state, 'Short'),
                'Entry Zone': f"{max(entry - 0.75*atr, close - 0.35*atr):.4f} - {entry:.4f}",
                'Invalidation': round(invalidation, 4),
                'Target': round(target, 4),
                'Holding Window': HOLDING_WINDOWS['long_term'],
                'Macro Aligned?': short_align,
                'macro_explanation': short_expl,
                'entry_mid': entry,
                'rr_score': round(rr, 2),
                'ev_score': round(rr * short_mult, 2),
                'route': overlay.get('next_route', '') or overlay.get('summary', ''),
                'why_now': 'Trend panjang turun dan downside masih lebih besar dari risk.',
                'why_not_yet': '',
            })

    # keep only execute-now candidates with macro not No
    valid = [x for x in candidates if x['Macro Aligned?'] in {'Yes','Mixed'}]
    if not valid:
        return None
    valid.sort(key=lambda x: (x['ev_score'], x['rr_score']), reverse=True)
    best = valid[0]
    best['current_price'] = round(close, 4)
    best['raw_states'] = f"S:{short_state} M:{mid_state} L:{long_state}"
    best['detail_kind'] = 'execute_now'
    return best

def _next_play(symbol: str, features: dict, overlay: dict) -> dict | None:
    close = features['last_close']
    atr = features['atr']
    short_state = features['short_state']
    mid_state = features['mid_state']
    long_state = features['long_state']
    long_align, long_mult, long_expl = macro_alignment_for_side('Long', overlay)
    short_align, short_mult, short_expl = macro_alignment_for_side('Short', overlay)

    nexts: list[dict] = []

    # Countertrend bounce in bearish macro/state
    if long_align != 'No' and features['bounce_from_tail'] and short_state in {'bearish','weakening','mixed'}:
        entry = max(features['tail_lrr'], features['trend_lrr'])
        invalidation = features['tail_lrr'] - 0.6 * atr
        target = features['trade_trr']
        rr = _rr(entry, invalidation, target, 'Long')
        if rr >= RISK_REWARD_MIN['next_play']:
            nexts.append({
                'Ticker': symbol, 'horizon_bucket': 'next_play', 'long_or_short': 'Long', 'next_flag': 1,
                'Bias': _pretty_bias(short_state, 'Long', countertrend=True),
                'Entry Zone': f"{entry:.4f} - {min(entry + 0.35*atr, features['trade_lrr']):.4f}",
                'Invalidation': round(invalidation, 4),
                'Target': round(target, 4),
                'Holding Window': HOLDING_WINDOWS['next_play'],
                'Macro Aligned?': 'Mixed' if long_align == 'Yes' else long_align,
                'macro_explanation': long_expl,
                'entry_mid': entry,
                'rr_score': round(rr, 2),
                'ev_score': round(rr * max(0.7, long_mult - 0.1), 2),
                'route': overlay.get('next_route', '') or overlay.get('summary', ''),
                'why_now': '',
                'why_not_yet': 'Pantulan dari cluster bawah valid, tapi ini countertrend. Tunggu pullback/reclaim yang lebih rapi; jangan kejar.',
                'detail_kind': 'next_play',
            })

    # Re-short or re-long after extension
    if short_align in {'Yes','Mixed'} and features['fade_from_top'] and short_state in {'bullish','improving','mixed'}:
        entry = min(features['tail_trr'], features['trend_trr'])
        invalidation = features['tail_trr'] + 0.6 * atr
        target = features['trade_lrr']
        rr = _rr(entry, invalidation, target, 'Short')
        if rr >= RISK_REWARD_MIN['next_play']:
            nexts.append({
                'Ticker': symbol, 'horizon_bucket': 'next_play', 'long_or_short': 'Short', 'next_flag': 1,
                'Bias': _pretty_bias(short_state, 'Short', countertrend=('Yes' not in {short_align})),
                'Entry Zone': f"{max(entry - 0.35*atr, features['trade_trr']):.4f} - {entry:.4f}",
                'Invalidation': round(invalidation, 4),
                'Target': round(target, 4),
                'Holding Window': HOLDING_WINDOWS['next_play'],
                'Macro Aligned?': short_align,
                'macro_explanation': short_expl,
                'entry_mid': entry,
                'rr_score': round(rr, 2),
                'ev_score': round(rr * short_mult, 2),
                'route': overlay.get('next_route', '') or overlay.get('summary', ''),
                'why_now': '',
                'why_not_yet': 'Arah besar masih cocok untuk short, tapi butuh rally/failure dulu supaya entry tidak telat.',
                'detail_kind': 'next_play',
            })

    if not nexts:
        return None
    nexts.sort(key=lambda x: (x['ev_score'], x['rr_score']), reverse=True)
    best = nexts[0]
    best['current_price'] = round(close, 4)
    best['raw_states'] = f"S:{short_state} M:{mid_state} L:{long_state}"
    return best

def _row_from_history(symbol: str, df: pd.DataFrame, overlay: dict) -> list[dict]:
    if df is None or df.empty or len(df) < MIN_HISTORY_BARS:
        return []
    features = compute_features(df.tail(400))
    rows = []
    current = _current_play(symbol, features, overlay)
    if current:
        rows.append(current)
    nxt = _next_play(symbol, features, overlay)
    if nxt:
        if not current or (current['Ticker'], current['long_or_short'], current['horizon_bucket']) != (nxt['Ticker'], nxt['long_or_short'], nxt['horizon_bucket']):
            rows.append(nxt)
    return rows

def build_market_snapshot(market: str, *, force_refresh: bool = False, use_cached_only: bool = True) -> tuple[pd.DataFrame, dict]:
    symbols = load_universe(market)
    refresh_report = {'requested': len(symbols), 'updated': 0, 'cached_only': 0, 'failed': []}
    if force_refresh and not use_cached_only:
        refresh_report = update_market_histories(market, symbols, force_refresh=True)
    histories = load_market_histories(market, symbols)
    macro_snapshot = load_macro_snapshot()
    overlay = market_macro_overlay(market, macro_snapshot)

    rows: list[dict] = []
    missing_due_to_history = []
    for symbol in symbols:
        df = histories.get(symbol)
        if df is None or df.empty:
            missing_due_to_history.append(symbol)
            continue
        rows.extend(_row_from_history(symbol, df, overlay))

    out = pd.DataFrame(rows)
    if out.empty:
        manifest = {
            'market': market,
            'as_of': datetime.now(timezone.utc).isoformat(),
            'universe': len(symbols),
            'eligible': 0,
            'coverage': round((len(histories) / max(len(symbols), 1)) * 100, 2),
            'macro_overlay': overlay,
            'history_status': history_status(market, symbols),
            'refresh_report': refresh_report,
            'missing_due_to_history': missing_due_to_history[:500],
            'required_columns': ['Ticker','Bias','Entry Zone','Invalidation','Target','Holding Window','Macro Aligned?','EV+ / R:R'],
        }
        save_snapshot(market, out, manifest)
        return out, manifest

    out['EV+ / R:R'] = out.apply(lambda r: f"{r['ev_score']:.2f} / {r['rr_score']:.2f}", axis=1)
    out = out.sort_values(['horizon_bucket','next_flag','ev_score','rr_score'], ascending=[True, True, False, False])

    manifest = {
        'market': market,
        'as_of': datetime.now(timezone.utc).isoformat(),
        'universe': len(symbols),
        'eligible': int(out['Ticker'].nunique()),
        'rows': int(len(out)),
        'coverage': round((len(histories) / max(len(symbols), 1)) * 100, 2),
        'macro_overlay': overlay,
        'history_status': history_status(market, symbols),
        'refresh_report': refresh_report,
        'missing_due_to_history': missing_due_to_history[:500],
        'required_columns': ['Ticker','Bias','Entry Zone','Invalidation','Target','Holding Window','Macro Aligned?','EV+ / R:R'],
        'note': 'App reads snapshots only. Heavy work is done by update/build scripts.',
    }
    save_snapshot(market, out, manifest)
    return out, manifest
