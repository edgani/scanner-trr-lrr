from __future__ import annotations

from typing import Dict
import math
import numpy as np
import pandas as pd


def safe_series(obj) -> pd.Series:
    if obj is None:
        return pd.Series(dtype=float)
    if isinstance(obj, pd.Series):
        return pd.to_numeric(obj, errors="coerce").dropna()
    if isinstance(obj, pd.DataFrame):
        cols = [c for c in ["Close", "Adj Close"] if c in obj.columns]
        if cols:
            return pd.to_numeric(obj[cols[0]], errors="coerce").dropna()
        nums = obj.select_dtypes(include=[np.number])
        if not nums.empty:
            return pd.to_numeric(nums.iloc[:, 0], errors="coerce").dropna()
    return pd.Series(dtype=float)


def ret_n(s: pd.Series, n: int) -> float:
    s = safe_series(s)
    if len(s) < n + 1:
        return float("nan")
    base = float(s.iloc[-(n + 1)])
    if not np.isfinite(base) or base == 0:
        return float("nan")
    return float(s.iloc[-1] / base - 1.0)


def delta_n(s: pd.Series, n: int) -> float:
    s = safe_series(s)
    if len(s) < n + 1:
        return float("nan")
    return float(s.iloc[-1] - s.iloc[-(n + 1)])


def trend_score(s: pd.Series) -> float:
    s = safe_series(s)
    if len(s) < 50:
        return 0.5
    px = float(s.iloc[-1])
    ma20 = float(s.rolling(20).mean().iloc[-1])
    ma50 = float(s.rolling(50).mean().iloc[-1])
    ma200 = float(s.rolling(200).mean().iloc[-1]) if len(s) >= 200 else ma50
    score = 0.0
    score += 0.25 if px > ma20 else 0.0
    score += 0.30 if px > ma50 else 0.0
    score += 0.30 if px > ma200 else 0.0
    score += 0.15 if ma20 > ma50 else 0.0
    return max(0.0, min(1.0, score))


def realized_vol(s: pd.Series, n: int = 20) -> float:
    s = safe_series(s)
    if len(s) < n + 1:
        return float("nan")
    r = s.pct_change().dropna().tail(n)
    if r.empty:
        return float("nan")
    return float(r.std() * math.sqrt(252.0))


def drawdown_score(s: pd.Series, lookback: int = 126) -> float:
    s = safe_series(s)
    if len(s) < 20:
        return 0.5
    s = s.tail(lookback)
    peak = s.cummax()
    dd = (s / peak - 1.0).min()
    if not np.isfinite(dd):
        return 0.5
    # 0 => no drawdown, 1 => very deep drawdown
    return max(0.0, min(1.0, abs(float(dd)) / 0.35))


def zscore_cross_section(values: Dict[str, float]) -> Dict[str, float]:
    clean = {k: float(v) for k, v in values.items() if isinstance(v, (int, float)) and np.isfinite(v)}
    if not clean:
        return {k: 0.0 for k in values}
    arr = np.array(list(clean.values()), dtype=float)
    mu = float(arr.mean())
    sd = float(arr.std())
    if sd < 1e-9:
        return {k: 0.0 for k in values}
    out = {}
    for k, v in values.items():
        if not isinstance(v, (int, float)) or not np.isfinite(v):
            out[k] = 0.0
        else:
            out[k] = float((float(v) - mu) / sd)
    return out


def clamp01(x: float) -> float:
    try:
        return max(0.0, min(1.0, float(x)))
    except Exception:
        return 0.0


def score_from_return(x: float, low: float = -0.1, high: float = 0.1) -> float:
    if not np.isfinite(x):
        return 0.5
    if x <= low:
        return 0.0
    if x >= high:
        return 1.0
    return float((x - low) / (high - low))


def rank_label(score: float) -> str:
    s = clamp01(score)
    if s >= 0.80:
        return "strong"
    if s >= 0.62:
        return "supportive"
    if s <= 0.20:
        return "very weak"
    if s <= 0.38:
        return "weak"
    return "mixed"
