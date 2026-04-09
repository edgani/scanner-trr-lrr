from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

MIN_RR_SHORT = 1.6
MIN_RR_MID = 2.0
MIN_RR_LONG = 2.5


def _atr(df: pd.DataFrame, n: int = 14) -> float:
    high, low, close = df['High'], df['Low'], df['Close']
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return float(tr.rolling(n).mean().iloc[-1])


def _rr_long(last: float, invalidation: float, target: float) -> float:
    risk = max(last - invalidation, 1e-9)
    reward = max(target - last, 0.0)
    return reward / risk


def _rr_short(last: float, invalidation: float, target: float) -> float:
    risk = max(invalidation - last, 1e-9)
    reward = max(last - target, 0.0)
    return reward / risk


def _horizon_from_setup(trend: str, macro_gate: str, no_chase: bool, strong_trend: bool) -> str:
    if no_chase or macro_gate in {'watch', 'countertrend_only'}:
        return 'next'
    if strong_trend and macro_gate in {'aligned', 'short_ok'}:
        return 'long'
    if trend in {'bullish', 'bearish'} and macro_gate in {'aligned', 'short_ok'}:
        return 'mid'
    if trend in {'transition_up', 'transition_down'}:
        return 'short'
    return 'next'


def _market_brain(brain: dict[str, Any], market: str) -> dict[str, Any]:
    key = 'forex' if market == 'forex' else market
    return ((brain.get('market_brains', {}) or {}).get(key) or {}).copy()


def build_rows(market: str, symbol: str, display_symbol: str, bucket: str, p1: dict[str, Any], df: pd.DataFrame, brain: dict[str, Any]) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    df = df.sort_index().copy()
    close = float(df['Close'].iloc[-1])
    atr = _atr(df)
    if not np.isfinite(close) or close <= 0 or not np.isfinite(atr) or atr <= 0:
        return []

    trend = str(p1.get('trend_fast', 'neutral'))
    location = str(p1.get('location_fast', 'unknown'))
    macro_gate = str(p1.get('macro_bucket_gate', 'neutral'))
    next_gate = str(p1.get('next_route_gate', 'off'))
    no_chase = str(p1.get('no_chase_flag', 'ok')) == 'no_chase'
    countertrend_watch = bool(p1.get('countertrend_watch', False))

    ma60 = float(df['Close'].rolling(60).mean().iloc[-1])
    ma200 = float(df['Close'].rolling(200).mean().iloc[-1])
    strong_trend = (trend == 'bullish' and close > ma60 > ma200) or (trend == 'bearish' and close < ma60 < ma200)
    mbrain = _market_brain(brain, market)
    route = str(mbrain.get('current_route') or brain.get('current_route') or '')
    next_route = str(mbrain.get('next_route') or brain.get('next_route') or '')
    invalidator = str(mbrain.get('invalidator_route') or brain.get('invalidator_route') or '')
    macro_expl = (
        f"Quad {brain.get('current_quad', 'unknown')} | route {route or '-'} | "
        f"next {next_route or '-'} | invalidator {invalidator or '-'} | "
        f"execution {mbrain.get('execution_mode') or brain.get('execution_mode', {}).get('label') or '-'} | "
        f"shock {mbrain.get('shock_state') or brain.get('shock_state') or '-'} | "
        f"health {mbrain.get('health_state') or brain.get('market_health') or '-'} | "
        f"crash {mbrain.get('crash_state') or brain.get('crash_state') or '-'}"
    )

    rows: list[dict[str, Any]] = []
    horizon = _horizon_from_setup(trend, macro_gate, no_chase, strong_trend)

    if trend in {'bullish', 'transition_up'} and macro_gate in {'aligned', 'neutral', 'watch'}:
        entry_low = max(close - 0.75 * atr, 0.0)
        entry_high = close + 0.10 * atr
        invalidation = close - (1.25 if horizon != 'long' else 1.75) * atr
        target = close + (1.6 if horizon == 'short' else 2.0 if horizon == 'mid' else 2.8 if horizon == 'long' else 1.3) * atr
        rr = _rr_long(close, invalidation, target)
        next_flag = no_chase or (horizon == 'next' and next_gate == 'on') or rr < (MIN_RR_LONG if horizon == 'long' else MIN_RR_MID if horizon == 'mid' else MIN_RR_SHORT)
        rows.append({
            'market': market,
            'symbol': symbol,
            'display_symbol': display_symbol,
            'bucket': bucket,
            'horizon_bucket': 'next' if next_flag else horizon,
            'long_or_short': 'long',
            'bias': 'Bullish' if macro_gate == 'aligned' else 'Bullish / Watch',
            'entry_zone': f'{entry_low:.4f} - {entry_high:.4f}',
            'invalidation': round(invalidation, 4),
            'target': round(target, 4),
            'holding_window': '2-7d' if (next_flag or horizon == 'short') else '2-6w' if horizon == 'mid' else '2-6m',
            'macro_aligned': 'YES' if macro_gate == 'aligned' else 'WATCH' if next_gate == 'on' else 'MIXED',
            'rr_score': round(rr, 2),
            'ev_score': round(rr * (0.9 if macro_gate == 'aligned' else 0.6 if next_gate == 'on' else 0.5), 2),
            'macro_score': 0.9 if macro_gate == 'aligned' else 0.6 if next_gate == 'on' else 0.5,
            'readiness_score': 0.4 if next_flag else 0.9,
            'conviction_score': 0.9 if strong_trend else 0.7,
            'penalty_score': 0.35 if no_chase else 0.0,
            'route': next_route if next_flag else route,
            'macro_explanation': macro_expl,
            'why_now': '' if next_flag else 'Trend, route, dan location masih cukup sinkron untuk long execution.',
            'why_not_yet': 'No chase. Tunggu reset / pullback / trigger route berikutnya.' if next_flag else '',
            'next_flag': next_flag,
            'countertrend': False,
            'as_of': p1.get('as_of'),
        })

    if trend in {'bearish', 'transition_down'} and macro_gate in {'aligned', 'short_ok', 'neutral', 'watch'}:
        entry_low = max(close - 0.10 * atr, 0.0)
        entry_high = close + 0.75 * atr
        invalidation = close + (1.25 if horizon != 'long' else 1.75) * atr
        target = close - (1.6 if horizon == 'short' else 2.0 if horizon == 'mid' else 2.8 if horizon == 'long' else 1.3) * atr
        rr = _rr_short(close, invalidation, target)
        short_bias_ok = macro_gate in {'aligned', 'short_ok'} or (macro_gate == 'neutral' and location == 'upper_range')
        next_flag = no_chase or not short_bias_ok or rr < (MIN_RR_LONG if horizon == 'long' else MIN_RR_MID if horizon == 'mid' else MIN_RR_SHORT)
        rows.append({
            'market': market,
            'symbol': symbol,
            'display_symbol': display_symbol,
            'bucket': bucket,
            'horizon_bucket': 'next' if next_flag else horizon,
            'long_or_short': 'short',
            'bias': 'Bearish' if macro_gate in {'aligned', 'short_ok'} else 'Bearish / Watch',
            'entry_zone': f'{entry_low:.4f} - {entry_high:.4f}',
            'invalidation': round(invalidation, 4),
            'target': round(target, 4),
            'holding_window': '2-7d' if (next_flag or horizon == 'short') else '2-6w' if horizon == 'mid' else '2-6m',
            'macro_aligned': 'YES' if macro_gate in {'aligned', 'short_ok'} else 'WATCH',
            'rr_score': round(rr, 2),
            'ev_score': round(rr * (0.9 if macro_gate in {'aligned', 'short_ok'} else 0.55), 2),
            'macro_score': 0.9 if macro_gate in {'aligned', 'short_ok'} else 0.55,
            'readiness_score': 0.4 if next_flag else 0.88,
            'conviction_score': 0.9 if strong_trend else 0.7,
            'penalty_score': 0.35 if no_chase else 0.0,
            'route': next_route if next_flag else route,
            'macro_explanation': macro_expl,
            'why_now': '' if next_flag else 'Macro backbone masih bearish/cut dan trend belum repair.',
            'why_not_yet': 'Rally / setup belum matang untuk short atau sudah terlalu jauh.' if next_flag else '',
            'next_flag': next_flag,
            'countertrend': False,
            'as_of': p1.get('as_of'),
        })

    if countertrend_watch and trend in {'bearish', 'transition_down'}:
        entry_low = max(close - 0.55 * atr, 0.0)
        entry_high = close + 0.10 * atr
        invalidation = close - 1.00 * atr
        target = close + 1.25 * atr
        rr = _rr_long(close, invalidation, target)
        next_flag = no_chase or location != 'lower_range' or rr < MIN_RR_SHORT
        rows.append({
            'market': market,
            'symbol': symbol,
            'display_symbol': display_symbol,
            'bucket': bucket,
            'horizon_bucket': 'next' if next_flag else 'short',
            'long_or_short': 'long',
            'bias': 'Countertrend Long',
            'entry_zone': f'{entry_low:.4f} - {entry_high:.4f}',
            'invalidation': round(invalidation, 4),
            'target': round(target, 4),
            'holding_window': '1-5d',
            'macro_aligned': 'COUNTERTREND',
            'rr_score': round(rr, 2),
            'ev_score': round(rr * 0.45, 2),
            'macro_score': 0.45,
            'readiness_score': 0.35 if next_flag else 0.72,
            'conviction_score': 0.45,
            'penalty_score': 0.25 if no_chase else 0.0,
            'route': 'Tail LRR / lower cluster bounce. Tactical only.',
            'macro_explanation': macro_expl,
            'why_now': '' if next_flag else 'Pantulan dekat lower cluster; ini tactical countertrend, bukan reversal call.',
            'why_not_yet': 'Bounce sudah lari. Pindah ke Next Plays Long / no chase.' if next_flag else '',
            'next_flag': next_flag,
            'countertrend': True,
            'as_of': p1.get('as_of'),
        })

    return rows
