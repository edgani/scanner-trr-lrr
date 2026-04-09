from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..config.pass2_thresholds import MIN_RR_SHORT, MIN_RR_MID, MIN_RR_LONG


def _atr(df: pd.DataFrame, n: int = 14) -> float:
    high, low, close = df['High'], df['Low'], df['Close']
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return float(tr.rolling(n).mean().iloc[-1])


def classify_horizon(trend_fast: str, macro_fast: str, late_flag: str) -> str:
    if late_flag == 'late':
        return 'next'
    if trend_fast in {'bullish', 'bearish'} and macro_fast == 'yes':
        return 'mid'
    if trend_fast in {'transition_up', 'transition_down'}:
        return 'short'
    return 'next'


def build_rows(market: str, symbol: str, display_symbol: str, bucket: str, p1: dict[str, Any], df: pd.DataFrame, brain: dict[str, Any], next_route: dict[str, Any]) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    df = df.sort_index().copy()
    close = float(df['Close'].iloc[-1])
    atr = _atr(df)
    if not np.isfinite(close) or close <= 0 or not np.isfinite(atr) or atr <= 0:
        return []
    ma20 = float(df['Close'].rolling(20).mean().iloc[-1])
    ma60 = float(df['Close'].rolling(60).mean().iloc[-1])
    last = close
    trend = p1['trend_fast']
    macro_fast = p1['macro_fast']
    horizon = classify_horizon(trend, macro_fast, p1['late_flag'])
    continuation_side = 'Long' if trend in {'bullish', 'transition_up'} else 'Short' if trend in {'bearish', 'transition_down'} else 'Flat'
    rows: list[dict[str, Any]] = []
    if continuation_side != 'Flat':
        if continuation_side == 'Long':
            entry_low, entry_high = max(last - 0.75 * atr, 0), last + 0.15 * atr
            invalidation = last - 1.25 * atr
            target = last + (2.0 if horizon == 'mid' else 1.5) * atr
            rr = max((target - last) / max(last - invalidation, 1e-9), 0.0)
            bias = 'Bullish' if macro_fast == 'yes' else 'Bullish / Mixed'
        else:
            entry_low, entry_high = last - 0.15 * atr, last + 0.75 * atr
            invalidation = last + 1.25 * atr
            target = last - (2.0 if horizon == 'mid' else 1.5) * atr
            rr = max((last - target) / max(invalidation - last, 1e-9), 0.0)
            bias = 'Bearish' if macro_fast == 'yes' else 'Bearish / Mixed'
        threshold = MIN_RR_MID if horizon == 'mid' else MIN_RR_SHORT
        next_flag = False
        why_not_yet = ''
        if p1['late_flag'] == 'late' or rr < threshold or macro_fast == 'no':
            horizon_use = 'next'
            next_flag = True
            why_not_yet = 'No chase / wait better location or macro confirmation.'
        else:
            horizon_use = horizon
        rows.append({
            'market': market,
            'symbol': symbol,
            'display_symbol': display_symbol,
            'bucket': bucket,
            'horizon_bucket': horizon_use,
            'long_or_short': continuation_side.lower(),
            'bias': bias,
            'entry_zone': f"{entry_low:.4f} - {entry_high:.4f}",
            'invalidation': round(invalidation, 4),
            'target': round(target, 4),
            'holding_window': '3-10d' if horizon_use == 'short' else '2-6w' if horizon_use == 'mid' else 'watch',
            'macro_aligned': macro_fast.upper(),
            'rr_score': round(rr, 2),
            'ev_score': round(rr * (1.0 if macro_fast == 'yes' else 0.65 if macro_fast == 'mixed' else 0.3), 2),
            'macro_score': 1.0 if macro_fast == 'yes' else 0.65 if macro_fast == 'mixed' else 0.3,
            'readiness_score': 1.0 if not next_flag else 0.45,
            'conviction_score': 0.9 if trend in {'bullish', 'bearish'} else 0.65,
            'penalty_score': 0.3 if p1['late_flag'] == 'late' else 0.0,
            'route': next_route.get('market_routes', {}).get(market, ''),
            'macro_explanation': f"Current quad {brain.get('current_quad', 'unknown')}; execution mode {brain.get('execution_mode', {})}",
            'why_now': 'Trend and macro are aligned enough for execution.' if not next_flag else '',
            'why_not_yet': why_not_yet,
            'next_flag': next_flag,
            'countertrend': False,
        })
    # countertrend bounce candidate
    if p1['location_fast'] == 'lower_range' and p1['macro_fast'] in {'no', 'mixed'} and trend in {'bearish', 'transition_down'}:
        entry_low, entry_high = max(last - 0.5 * atr, 0), last + 0.1 * atr
        invalidation = last - 1.0 * atr
        target = last + 1.25 * atr
        rr = max((target - last) / max(last - invalidation, 1e-9), 0.0)
        rows.append({
            'market': market,
            'symbol': symbol,
            'display_symbol': display_symbol,
            'bucket': bucket,
            'horizon_bucket': 'short' if p1['late_flag'] != 'late' and rr >= MIN_RR_SHORT else 'next',
            'long_or_short': 'long',
            'bias': 'Countertrend Long',
            'entry_zone': f"{entry_low:.4f} - {entry_high:.4f}",
            'invalidation': round(invalidation, 4),
            'target': round(target, 4),
            'holding_window': '1-5d',
            'macro_aligned': 'MIXED',
            'rr_score': round(rr, 2),
            'ev_score': round(rr * 0.45, 2),
            'macro_score': 0.45,
            'readiness_score': 0.7 if p1['late_flag'] != 'late' else 0.3,
            'conviction_score': 0.45,
            'penalty_score': 0.35,
            'route': 'Tail LRR / lower-cluster bounce; treat as tactical only.',
            'macro_explanation': 'Macro remains weaker; bounce is tactical countertrend, not a structural reversal.',
            'why_now': 'Bounce from lower cluster / tail area.' if p1['late_flag'] != 'late' else '',
            'why_not_yet': 'No chase after rebound has already stretched.' if p1['late_flag'] == 'late' else '',
            'next_flag': p1['late_flag'] == 'late',
            'countertrend': True,
        })
    return rows
