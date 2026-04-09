from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd

from ..scanner.sanity import evaluate_history_sanity

MIN_BARS = 200
US_MIN_AVG_DOLLAR_VOL = 2_000_000
IHSG_MIN_AVG_DOLLAR_VOL = 200_000
CRYPTO_MIN_USD_VOL = 1_000_000
MAX_LATE_DISTANCE_ATR = 2.5


@dataclass
class Pass1Result:
    symbol: str
    market: str
    bucket: str
    data_ok: bool
    fresh_ok: bool
    history_ok: bool
    liquidity_ok: bool
    tradable_ok: bool
    trend_fast: str
    vol_regime_fast: str
    location_fast: str
    macro_bucket_gate: str
    next_route_gate: str
    no_chase_flag: str
    countertrend_watch: bool
    pass1_score: float
    reject_reason: str
    as_of: str | None
    age_days: int | None


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    high, low, close = df['High'], df['Low'], df['Close']
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def _trend_state(close: pd.Series) -> tuple[str, float]:
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    ma200 = close.rolling(200).mean()
    r20 = float(close.pct_change(20).iloc[-1]) if len(close) > 20 else 0.0
    last = float(close.iloc[-1])
    if last > ma20.iloc[-1] > ma60.iloc[-1] > ma200.iloc[-1] and r20 > 0.04:
        return 'bullish', 1.0
    if last < ma20.iloc[-1] < ma60.iloc[-1] < ma200.iloc[-1] and r20 < -0.04:
        return 'bearish', 1.0
    if r20 > 0.02:
        return 'transition_up', 0.65
    if r20 < -0.02:
        return 'transition_down', 0.65
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


def _liquidity_ok(market: str, df: pd.DataFrame) -> bool:
    vol = pd.to_numeric(df.get('Volume', pd.Series(0, index=df.index)), errors='coerce').fillna(0.0)
    dollar_vol = (pd.to_numeric(df['Close'], errors='coerce').fillna(0.0) * vol).tail(20).mean()
    if market == 'us':
        return bool(dollar_vol >= US_MIN_AVG_DOLLAR_VOL)
    if market == 'ihsg':
        return bool(dollar_vol >= IHSG_MIN_AVG_DOLLAR_VOL)
    if market == 'crypto':
        return bool(dollar_vol >= CRYPTO_MIN_USD_VOL)
    return True


def _macro_gate(bucket: str, trend_fast: str, location_fast: str, policy: dict[str, Any]) -> tuple[str, str, bool, float]:
    supportive = set(policy.get('supportive_buckets', set()))
    next_buckets = set(policy.get('next_buckets', set()))
    cut = set(policy.get('cut_buckets', set()))
    short_buckets = set(policy.get('short_buckets', set()))

    countertrend_watch = False
    if bucket in supportive:
        return 'aligned', 'off', False, 1.0
    if bucket in next_buckets:
        return 'watch', 'on', False, 0.65
    if bucket in cut:
        if location_fast == 'lower_range' and trend_fast in {'bearish', 'transition_down'}:
            countertrend_watch = True
            return 'countertrend_only', 'on', True, 0.45
        if trend_fast in {'bearish', 'transition_down'} and bucket in short_buckets:
            return 'short_ok', 'off', False, 0.55
        return 'cut', 'off', False, 0.10
    if bucket in short_buckets and trend_fast in {'bearish', 'transition_down'}:
        return 'short_ok', 'off', False, 0.55
    return 'neutral', 'off', False, 0.50


def evaluate_one(market: str, bucket: str, df: pd.DataFrame | None, policy: dict[str, Any], tradable_hint: bool = True) -> Pass1Result:
    symbol = str(getattr(df, 'attrs', {}).get('symbol', 'UNKNOWN')) if df is not None else 'UNKNOWN'
    if df is None or df.empty:
        return Pass1Result(symbol, market, bucket, False, False, False, False, False, 'invalid', 'invalid', 'unknown', 'cut', 'off', 'no_chase', False, 0.0, 'missing_history', None, None)

    df = df.sort_index().copy()
    sanity = evaluate_history_sanity(market, df)
    history_ok = len(df) >= MIN_BARS
    data_ok = all(c in df.columns for c in ['Open', 'High', 'Low', 'Close']) and float(pd.to_numeric(df['Close'], errors='coerce').iloc[-1]) > 0
    tradable_ok = bool(tradable_hint)
    liquidity_ok = _liquidity_ok(market, df)
    trend_fast, trend_score = _trend_state(pd.to_numeric(df['Close'], errors='coerce').dropna())
    location_fast, location_score = _location(pd.to_numeric(df['Close'], errors='coerce').dropna())

    atr = _atr(df).iloc[-1]
    atr_pct = float(atr / max(df['Close'].iloc[-1], 1e-9)) if pd.notna(atr) and float(df['Close'].iloc[-1]) > 0 else 0.0
    vol_regime_fast = 'high' if atr_pct > 0.05 else 'normal' if atr_pct > 0.015 else 'low'
    ma20 = df['Close'].rolling(20).mean().iloc[-1]
    late_dist = abs(float(df['Close'].iloc[-1] - ma20)) / max(float(atr) if pd.notna(atr) and atr > 0 else 1.0, 1e-9)
    execution_no_chase = bool(policy.get('no_chase_default', False))
    no_chase_flag = 'no_chase' if execution_no_chase and late_dist > 1.5 or late_dist > MAX_LATE_DISTANCE_ATR else 'ok'

    macro_gate, next_gate, countertrend_watch, macro_score = _macro_gate(bucket, trend_fast, location_fast, policy)

    reject_reason = ''
    if not data_ok:
        reject_reason = 'bad_ohlc'
    elif not sanity.fresh_ok:
        reject_reason = sanity.reason or 'stale_last_bar'
    elif not sanity.absurd_ok:
        reject_reason = sanity.reason or 'absurd_last_move'
    elif not history_ok:
        reject_reason = 'not_enough_history'
    elif not tradable_ok:
        reject_reason = 'not_tradable'
    elif not liquidity_ok:
        reject_reason = 'illiquid'
    elif bool(policy.get('no_trade', False)):
        reject_reason = 'macro_no_trade'
    elif macro_gate == 'cut' and not countertrend_watch:
        reject_reason = 'macro_cut'

    score = (
        0.22 * trend_score
        + 0.16 * location_score
        + 0.24 * macro_score
        + 0.12 * (1.0 if liquidity_ok else 0.0)
        + 0.12 * (1.0 if sanity.fresh_ok else 0.0)
        + 0.08 * (1.0 if tradable_ok else 0.0)
        + 0.06 * (0.0 if no_chase_flag == 'no_chase' else 1.0)
    )
    if reject_reason:
        score = 0.0

    return Pass1Result(
        symbol=symbol,
        market=market,
        bucket=bucket,
        data_ok=data_ok,
        fresh_ok=sanity.fresh_ok,
        history_ok=history_ok,
        liquidity_ok=liquidity_ok,
        tradable_ok=tradable_ok,
        trend_fast=trend_fast,
        vol_regime_fast=vol_regime_fast,
        location_fast=location_fast,
        macro_bucket_gate=macro_gate,
        next_route_gate=next_gate,
        no_chase_flag=no_chase_flag,
        countertrend_watch=countertrend_watch,
        pass1_score=round(float(score), 4),
        reject_reason=reject_reason,
        as_of=sanity.as_of,
        age_days=sanity.age_days,
    )


def results_to_frame(results: Iterable[Pass1Result]) -> pd.DataFrame:
    return pd.DataFrame([r.__dict__ for r in results])
