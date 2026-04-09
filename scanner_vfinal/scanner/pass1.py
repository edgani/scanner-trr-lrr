from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from ..config.pass1_thresholds import MIN_BARS, US_MIN_AVG_DOLLAR_VOL, IHSG_MIN_AVG_DOLLAR_VOL, CRYPTO_MIN_USD_VOL, MAX_LATE_DISTANCE_ATR
from .brain import bucket_policy


@dataclass
class Pass1Result:
    symbol: str
    market: str
    bucket: str
    data_ok: bool
    fresh_ok: bool
    liquidity_ok: bool
    trend_fast: str
    vol_regime_fast: str
    location_fast: str
    macro_fast: str
    late_flag: str
    pass1_score: float
    reject_reason: str


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    high, low, close = df['High'], df['Low'], df['Close']
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def _trend_state(close: pd.Series) -> tuple[str, float]:
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    r20 = close.pct_change(20).iloc[-1]
    if close.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1] and r20 > 0:
        return 'bullish', 1.0
    if close.iloc[-1] < ma20.iloc[-1] < ma60.iloc[-1] and r20 < 0:
        return 'bearish', 1.0
    if r20 > 0:
        return 'transition_up', 0.6
    if r20 < 0:
        return 'transition_down', 0.6
    return 'neutral', 0.4


def _location(close: pd.Series) -> tuple[str, float]:
    r60_low = close.rolling(60).min().iloc[-1]
    r60_high = close.rolling(60).max().iloc[-1]
    last = close.iloc[-1]
    if pd.isna(r60_low) or pd.isna(r60_high) or r60_high <= r60_low:
        return 'unknown', 0.0
    pos = (last - r60_low) / max(r60_high - r60_low, 1e-9)
    if pos <= 0.2:
        return 'lower_range', 1.0
    if pos >= 0.8:
        return 'upper_range', 1.0
    return 'mid_range', 0.6


def evaluate_one(market: str, bucket: str, df: pd.DataFrame, policy: dict[str, set[str]]) -> Pass1Result:
    symbol = str(df.attrs.get('symbol', 'UNKNOWN'))
    if df is None or df.empty or len(df) < MIN_BARS:
        return Pass1Result(symbol, market, bucket, False, False, False, 'invalid', 'invalid', 'unknown', 'no', 'late', 0.0, 'not_enough_history')
    df = df.sort_index().copy()
    data_ok = all(c in df.columns for c in ['Open', 'High', 'Low', 'Close']) and float(df['Close'].iloc[-1]) > 0
    fresh_ok = True
    avg_dollar_vol = float((df['Close'] * df.get('Volume', pd.Series(0, index=df.index))).tail(20).mean()) if 'Volume' in df.columns else np.nan
    if market == 'us':
        liquidity_ok = bool(avg_dollar_vol >= US_MIN_AVG_DOLLAR_VOL)
    elif market == 'ihsg':
        liquidity_ok = bool(avg_dollar_vol >= IHSG_MIN_AVG_DOLLAR_VOL)
    elif market == 'crypto':
        liquidity_ok = bool(avg_dollar_vol >= CRYPTO_MIN_USD_VOL) if not np.isnan(avg_dollar_vol) else True
    else:
        liquidity_ok = True
    trend_fast, trend_score = _trend_state(df['Close'])
    location_fast, location_score = _location(df['Close'])
    atr = _atr(df).iloc[-1]
    atr_pct = float(atr / max(df['Close'].iloc[-1], 1e-9)) if pd.notna(atr) else 0.0
    vol_regime_fast = 'high' if atr_pct > 0.05 else 'normal' if atr_pct > 0.015 else 'low'
    ma20 = df['Close'].rolling(20).mean().iloc[-1]
    late_dist = abs(float(df['Close'].iloc[-1] - ma20)) / max(float(atr) if pd.notna(atr) and atr > 0 else 1.0, 1e-9)
    late_flag = 'late' if late_dist > MAX_LATE_DISTANCE_ATR else 'ok'
    if bucket in policy['supportive']:
        macro_fast, macro_score = 'yes', 1.0
    elif bucket in policy['hostile']:
        macro_fast, macro_score = 'no', 0.2
    elif bucket in policy['next']:
        macro_fast, macro_score = 'mixed', 0.6
    else:
        macro_fast, macro_score = 'mixed', 0.5
    reject_reason = ''
    if not data_ok:
        reject_reason = 'bad_ohlc'
    elif not liquidity_ok:
        reject_reason = 'illiquid'
    elif macro_fast == 'no' and trend_fast == 'neutral':
        reject_reason = 'hostile_macro_no_trend'
    pass1_score = 0.0 if reject_reason else (0.25 * trend_score + 0.2 * location_score + 0.3 * macro_score + 0.15 * (1.0 if liquidity_ok else 0.0) + 0.1 * (0.0 if late_flag == 'late' else 1.0))
    return Pass1Result(symbol, market, bucket, data_ok, fresh_ok, liquidity_ok, trend_fast, vol_regime_fast, location_fast, macro_fast, late_flag, pass1_score, reject_reason)


def results_to_frame(results: Iterable[Pass1Result]) -> pd.DataFrame:
    return pd.DataFrame([r.__dict__ for r in results])
