from __future__ import annotations
import numpy as np
import pandas as pd

def _state_from_stack(close: float, fast: float, mid: float, slow: float, mom_fast: float, mom_slow: float) -> str:
    if close > fast > mid > slow and mom_fast > 0 and mom_slow > 0:
        return 'bullish'
    if close < fast < mid < slow and mom_fast < 0 and mom_slow < 0:
        return 'bearish'
    if close > mid and mom_fast > 0:
        return 'improving'
    if close < mid and mom_fast < 0:
        return 'weakening'
    return 'mixed'

def compute_features(df: pd.DataFrame) -> dict:
    x = df.copy().dropna(subset=['Close'])
    close = x['Close'].astype(float)
    high = x['High'].astype(float)
    low = x['Low'].astype(float)
    volume = x['Volume'].astype(float) if 'Volume' in x else pd.Series(0.0, index=x.index)

    ema10 = close.ewm(span=10, adjust=False).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()
    tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean().fillna(tr.expanding().mean())
    mom10 = close.pct_change(10).fillna(0.0)
    mom20 = close.pct_change(20).fillna(0.0)
    mom60 = close.pct_change(60).fillna(0.0)
    vol20 = volume.rolling(20).mean().replace(0, np.nan)
    vol_ratio = (volume / vol20).replace([np.inf, -np.inf], np.nan).fillna(1.0)

    last_close = float(close.iloc[-1])
    atr = float(atr14.iloc[-1]) if float(atr14.iloc[-1]) == float(atr14.iloc[-1]) else max(last_close * 0.02, 0.01)

    ema10v = float(ema10.iloc[-1]); ema20v = float(ema20.iloc[-1]); ema50v = float(ema50.iloc[-1]); ema200v = float(ema200.iloc[-1])
    mom10v = float(mom10.iloc[-1]); mom20v = float(mom20.iloc[-1]); mom60v = float(mom60.iloc[-1])
    atr_pct = atr / max(last_close, 1e-9)
    vol_ratio_v = float(vol_ratio.iloc[-1]) if float(vol_ratio.iloc[-1]) == float(vol_ratio.iloc[-1]) else 1.0

    short_state = _state_from_stack(last_close, ema10v, ema20v, ema50v, mom10v, mom20v)
    mid_state = _state_from_stack(last_close, ema20v, ema50v, ema200v, mom20v, mom60v)
    long_state = _state_from_stack(last_close, ema50v, ema200v, ema200v, mom60v, mom60v)

    trade_lrr = ema20v - 1.5 * atr
    trade_trr = ema20v + 1.5 * atr
    trend_lrr = ema50v - 2.0 * atr
    trend_trr = ema50v + 2.0 * atr
    position_lrr = ema200v - 3.0 * atr
    position_trr = ema200v + 3.0 * atr
    tail_lrr = min(trend_lrr, position_lrr) - 0.75 * atr
    tail_trr = max(trend_trr, position_trr) + 0.75 * atr

    dist_trade_low = (last_close - trade_lrr) / max(atr, 1e-9)
    dist_trade_high = (trade_trr - last_close) / max(atr, 1e-9)
    dist_lower_cluster = (last_close - min(trend_lrr, position_lrr, tail_lrr)) / max(atr, 1e-9)
    dist_upper_cluster = (max(trend_trr, position_trr, tail_trr) - last_close) / max(atr, 1e-9)
    bounce_from_tail = dist_lower_cluster <= 1.2 and mom10v > -0.02
    fade_from_top = dist_upper_cluster <= 1.2 and mom10v < 0.02

    return {
        'last_close': last_close,
        'ema10': ema10v,
        'ema20': ema20v,
        'ema50': ema50v,
        'ema200': ema200v,
        'atr': atr,
        'atr_pct': atr_pct,
        'mom10': mom10v,
        'mom20': mom20v,
        'mom60': mom60v,
        'vol_ratio': vol_ratio_v,
        'short_state': short_state,
        'mid_state': mid_state,
        'long_state': long_state,
        'trade_lrr': trade_lrr,
        'trade_trr': trade_trr,
        'trend_lrr': trend_lrr,
        'trend_trr': trend_trr,
        'position_lrr': position_lrr,
        'position_trr': position_trr,
        'tail_lrr': tail_lrr,
        'tail_trr': tail_trr,
        'dist_trade_low': dist_trade_low,
        'dist_trade_high': dist_trade_high,
        'dist_lower_cluster': dist_lower_cluster,
        'dist_upper_cluster': dist_upper_cluster,
        'bounce_from_tail': bounce_from_tail,
        'fade_from_top': fade_from_top,
    }
