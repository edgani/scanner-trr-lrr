from __future__ import annotations
from typing import Iterable
import math
import pandas as pd
from config.display_names import DISPLAY_NAME_MAP


def _series(prices: dict, symbol: str, price_frames: dict | None = None) -> pd.Series:
    s = prices.get(symbol)
    if s is None and price_frames:
        s = price_frames.get(symbol)
    if isinstance(s, pd.Series):
        return pd.to_numeric(s, errors="coerce").dropna()
    if isinstance(s, pd.DataFrame) and 'Close' in s.columns:
        return pd.to_numeric(s['Close'], errors='coerce').dropna()
    return pd.Series(dtype=float)


def _ret(s: pd.Series, n: int) -> float:
    if len(s) < n + 1:
        return 0.0
    base = float(s.iloc[-(n + 1)])
    if not math.isfinite(base) or base == 0:
        return 0.0
    return float(s.iloc[-1] / base - 1.0)


def _vol(s: pd.Series, n: int = 21) -> float:
    if len(s) < n + 1:
        return 0.0
    r = s.pct_change().dropna().tail(n)
    return float(r.std()) if not r.empty else 0.0


def _downside_vol(s: pd.Series, n: int = 21) -> float:
    if len(s) < n + 1:
        return 0.0
    r = s.pct_change().dropna().tail(n)
    r = r[r < 0]
    return float(r.std()) if not r.empty else 0.0


def _trend(s: pd.Series) -> float:
    if len(s) < 120:
        return 0.0
    px = float(s.iloc[-1])
    ma20 = float(s.rolling(20).mean().iloc[-1])
    ma50 = float(s.rolling(50).mean().iloc[-1])
    ma100 = float(s.rolling(100).mean().iloc[-1])
    score = 0.0
    score += 0.30 if px > ma20 else 0.0
    score += 0.35 if px > ma50 else 0.0
    score += 0.35 if px > ma100 else 0.0
    if ma20 > ma50 > ma100:
        score += 0.15
    elif ma20 > ma50:
        score += 0.05
    return max(0.0, min(1.0, score))


def _efficiency_ratio(s: pd.Series, n: int = 21) -> float:
    if len(s) < n + 1:
        return 0.0
    win = s.iloc[-(n + 1):]
    direction = abs(float(win.iloc[-1] - win.iloc[0]))
    path = float(win.diff().abs().dropna().sum())
    if path <= 0:
        return 0.0
    return max(0.0, min(1.0, direction / path))


def _dist_from_high(s: pd.Series, n: int = 63) -> float:
    if len(s) < n:
        return 0.0
    high = float(s.tail(n).max())
    if high <= 0:
        return 0.0
    return float(s.iloc[-1] / high - 1.0)


def _dist_from_low(s: pd.Series, n: int = 63) -> float:
    if len(s) < n:
        return 0.0
    low = float(s.tail(n).min())
    if low <= 0:
        return 0.0
    return float(s.iloc[-1] / low - 1.0)


def _tanh_scale(x: float, scale: float) -> float:
    if not math.isfinite(x):
        return 0.0
    if scale <= 0:
        return 0.0
    return float(math.tanh(x / scale))


def _range_terms(symbol: str, prices: dict, price_frames: dict | None, asset_ranges: dict | None) -> tuple[dict, float]:
    ranges = asset_ranges or {}
    rng = ranges.get(symbol, {}) or {}
    s = _series(prices, symbol, price_frames)
    if s.empty:
        return {
            'trade_mid': None,
            'trade_low': None,
            'trade_high': None,
            'trend_low': None,
            'trend_high': None,
            'tail_floor': None,
            'tail_ceiling': None,
            'range_quality': 0.5,
            'stretch_state': 'neutral',
            'range_state': 'unknown',
            'trend_state': 'unknown',
            'break_state': 'unknown',
            'signal_confidence': 0.5,
            'volume_confirm': 0.5,
            'range_location': 0.5,
            'reclaim_quality': 0.0,
            'breakout_quality': 0.0,
            'breakdown_quality': 0.0,
            'stretch_penalty': 0.0,
        }, 0.0
    px = float(s.iloc[-1])
    trade_low = rng.get('trade_low')
    trade_mid = rng.get('trade_mid')
    trade_high = rng.get('trade_high')
    band = None
    if isinstance(trade_low, (int, float)) and isinstance(trade_high, (int, float)) and math.isfinite(trade_low) and math.isfinite(trade_high):
        band = max(trade_high - trade_low, 1e-9)
        range_location = max(0.0, min(1.0, (px - trade_low) / band))
    else:
        range_location = 0.5
    break_state = str(rng.get('break_state', 'unknown'))
    trend_state = str(rng.get('trend_state', 'unknown'))
    signal_confidence = float(rng.get('signal_confidence', 0.5) or 0.5)
    volume_confirm = float(rng.get('volume_confirm', 0.5) or 0.5)
    reclaim_quality = 0.0
    breakout_quality = 0.0
    breakdown_quality = 0.0
    if isinstance(trade_mid, (int, float)) and math.isfinite(trade_mid) and px > trade_mid:
        reclaim_quality = min(max((px / max(trade_mid, 1e-9) - 1.0) / 0.04, 0.0), 1.0) * signal_confidence
    if break_state in {'trade_breakout', 'upside_escape'}:
        breakout_quality = 0.6 * signal_confidence + 0.4 * volume_confirm
    if break_state in {'trade_breakdown', 'downside_break'}:
        breakdown_quality = 0.6 * signal_confidence + 0.4 * (1.0 - max(0.0, min(range_location, 1.0)))
    stretch_state = str(rng.get('stretch_state', 'neutral'))
    stretch_penalty = 0.0
    if stretch_state in {'extended', 'overbought'}:
        stretch_penalty = 0.65
    elif stretch_state == 'oversold':
        stretch_penalty = 0.15
    signal_bonus = 0.0
    if trend_state == 'bullish':
        signal_bonus += 0.05
    elif trend_state == 'bearish':
        signal_bonus -= 0.05
    return {
        'trade_mid': trade_mid,
        'trade_low': trade_low,
        'trade_high': trade_high,
        'trend_low': rng.get('trend_low'),
        'trend_high': rng.get('trend_high'),
        'tail_floor': rng.get('tail_floor'),
        'tail_ceiling': rng.get('tail_ceiling'),
        'range_quality': float(rng.get('range_quality', 0.5) or 0.5),
        'stretch_state': stretch_state,
        'range_state': str(rng.get('range_state', 'unknown')),
        'trend_state': trend_state,
        'break_state': break_state,
        'signal_confidence': signal_confidence,
        'volume_confirm': volume_confirm,
        'range_location': range_location,
        'reclaim_quality': reclaim_quality,
        'breakout_quality': breakout_quality,
        'breakdown_quality': breakdown_quality,
        'stretch_penalty': stretch_penalty,
    }, signal_bonus


def _context_adjustment(symbol: str, context: dict | None) -> tuple[float, dict]:
    ctx = context or {}
    regime_score = float(ctx.get("regime_score", 0.5) or 0.5)
    breadth_score = float(ctx.get("breadth_score", 0.5) or 0.5)
    execution_score = float(ctx.get("execution_score", 0.5) or 0.5)
    risk_off_penalty = float(ctx.get("risk_off_penalty", 0.0) or 0.0)
    crash_penalty = float(ctx.get("crash_penalty", 0.0) or 0.0)
    theme_boost = float((ctx.get("theme_boosts", {}) or {}).get(symbol, 0.0) or 0.0)
    symbol_adj = float((ctx.get("symbol_adjustments", {}) or {}).get(symbol, 0.0) or 0.0)
    symbol_flag = str((ctx.get("symbol_flags", {}) or {}).get(symbol, "") or "")
    symbol_meta = (ctx.get("symbol_meta", {}) or {}).get(symbol, {}) or {}
    context_adj = (
        0.09 * (regime_score - 0.5)
        + 0.07 * (breadth_score - 0.5)
        + 0.07 * (execution_score - 0.5)
        - 0.16 * risk_off_penalty
        - 0.12 * crash_penalty
        + theme_boost
        + symbol_adj
    )
    return context_adj, {
        "regime_score": regime_score,
        "breadth_score": breadth_score,
        "execution_score": execution_score,
        "risk_off_penalty": risk_off_penalty,
        "crash_penalty": crash_penalty,
        "theme_boost": theme_boost,
        "structural_adj": symbol_adj,
        "structural_flag": symbol_flag,
        "structural_meta": symbol_meta,
    }


def rank_symbols(prices: dict, symbols: Iterable[str], top_n: int = 12, context: dict | None = None, price_frames: dict | None = None, asset_ranges: dict | None = None) -> tuple[list[dict], list[dict]]:
    rows = []
    seen = set()
    ctx_asset_ranges = asset_ranges or ((context or {}).get('_asset_ranges', {}) or {})
    for sym in symbols:
        if sym in seen:
            continue
        seen.add(sym)
        s = _series(prices, sym, price_frames)
        if s.empty:
            continue
        r5 = _ret(s, 5)
        r21 = _ret(s, 21)
        r63 = _ret(s, 63)
        r126 = _ret(s, 126)
        v21 = _vol(s, 21)
        dv21 = _downside_vol(s, 21)
        trend = _trend(s)
        eff = _efficiency_ratio(s, 21)
        dist_high63 = _dist_from_high(s, 63)
        dist_low63 = _dist_from_low(s, 63)
        exhaustion = max(0.0, _tanh_scale(max(0.0, r5) + max(0.0, r21 - 0.5 * r63), 0.18))
        range_meta, signal_bonus = _range_terms(sym, prices, price_frames, ctx_asset_ranges)
        native_signal = (
            0.20 * _tanh_scale(r63, 0.32)
            + 0.14 * _tanh_scale(r21, 0.18)
            + 0.08 * _tanh_scale(r126, 0.55)
            + 0.16 * (2.0 * trend - 1.0)
            + 0.10 * (2.0 * eff - 1.0)
            + 0.08 * _tanh_scale(dist_low63, 0.45)
            + 0.04 * _tanh_scale(dist_high63, 0.18)
            + 0.08 * (2.0 * range_meta['reclaim_quality'] - 1.0)
            + 0.08 * range_meta['breakout_quality']
            - 0.08 * range_meta['breakdown_quality']
            + 0.06 * (2.0 * range_meta['volume_confirm'] - 1.0)
            - 0.06 * _tanh_scale(v21, 0.08)
            - 0.05 * _tanh_scale(dv21, 0.06)
            - 0.08 * range_meta['stretch_penalty']
            - 0.04 * exhaustion
            + signal_bonus
        )
        base_score = native_signal
        context_adj, ctx_meta = _context_adjustment(sym, context)
        score = base_score + context_adj
        rows.append({
            "symbol": sym,
            "name": DISPLAY_NAME_MAP.get(sym, sym),
            "score": float(score),
            "base_score": float(base_score),
            "context_adj": float(context_adj),
            "r5": float(r5),
            "r21": float(r21),
            "r63": float(r63),
            "r126": float(r126),
            "vol21": float(v21),
            "downside_vol21": float(dv21),
            "trend": float(trend),
            "efficiency": float(eff),
            "dist_high63": float(dist_high63),
            "dist_low63": float(dist_low63),
            "exhaustion": float(exhaustion),
            **range_meta,
            **ctx_meta,
        })
    rows = sorted(rows, key=lambda x: x["score"], reverse=True)
    return rows[:top_n], list(reversed(rows[-top_n:]))


def classify_side(score: float, neutral_band: float = 0.03) -> str:
    if score >= neutral_band:
        return 'long'
    if score <= -neutral_band:
        return 'short'
    return 'neutral'


def classify_action(score: float, side: str = 'long') -> str:
    side = (side or 'long').lower()
    if side == 'short':
        if score <= -0.26:
            return 'Short Now'
        if score <= -0.16:
            return 'Short on Bounce'
        if score <= -0.07:
            return 'Wait Short Reclaim'
        if score <= 0.04:
            return 'Tactical Short'
        return 'Avoid Short'

    if score >= 0.26:
        return 'Long Now'
    if score >= 0.16:
        return 'Long on Reset'
    if score >= 0.07:
        return 'Wait Long Reclaim'
    if score >= -0.04:
        return 'Tactical Long'
    return 'Avoid Long'


def classify_radar(score: float) -> str:
    if score >= 0.16:
        return 'Hidden Leader'
    if score >= 0.07:
        return 'Almost Ready'
    if score >= -0.02:
        return 'Needs Reset'
    if score >= -0.12:
        return 'Crowded/Fading'
    return 'Fragile'
