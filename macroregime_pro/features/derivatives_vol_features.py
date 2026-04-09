from __future__ import annotations
from typing import Dict
import numpy as np
import pandas as pd

from config.weights import DERIVATIVES_VOL_WEIGHTS
from utils.math_utils import clamp01


def _safe_series(s) -> pd.Series:
    if s is None:
        return pd.Series(dtype=float)
    if isinstance(s, pd.Series):
        return pd.to_numeric(s, errors="coerce").dropna()
    return pd.Series(dtype=float)


def _last_or_nan(s: pd.Series) -> float:
    return float(s.iloc[-1]) if len(s) else float("nan")


def _score_vix_level(vix_last: float) -> float:
    if not np.isfinite(vix_last):
        return 0.5
    return clamp01((float(vix_last) - 14.0) / 18.0)


def _weighted_mean(parts: Dict[str, float], weights: Dict[str, float]) -> float:
    total = sum(max(0.0, float(weights.get(k, 0.0))) for k in parts) or 1.0
    acc = sum(float(parts[k]) * max(0.0, float(weights.get(k, 0.0))) for k in parts)
    return clamp01(acc / total)


def build_derivatives_vol_features(prices: Dict[str, pd.Series], market: Dict[str, float]) -> Dict[str, float]:
    vix = _safe_series(prices.get("^VIX"))
    vvix = _safe_series(prices.get("^VVIX"))
    skew = _safe_series(prices.get("SKEW"))
    vix3m = _safe_series(prices.get("^VIX3M"))
    spy = _safe_series(prices.get("SPY"))

    vix_last = _last_or_nan(vix)
    vvix_last = _last_or_nan(vvix)
    skew_last = _last_or_nan(skew)
    vix3m_last = _last_or_nan(vix3m)

    rv20 = 0.0
    if len(spy) >= 25:
        rets = spy.pct_change().dropna()
        if len(rets) >= 20:
            rv20 = float(rets.tail(20).std() * np.sqrt(252.0) * 100.0)

    iv_rv_ratio = float(vix_last / rv20) if np.isfinite(vix_last) and rv20 > 1e-9 else 1.0
    iv_premium = clamp01((iv_rv_ratio - 1.0) / 0.60)

    vix_level = _score_vix_level(vix_last)
    vix_trend = clamp01(0.5 + float(market.get("vix_1m", 0.0)) / 0.20)
    narrow_leadership = clamp01(float(market.get("narrow_leadership", 0.5)))

    if np.isfinite(vvix_last):
        vvix_proxy = clamp01((vvix_last - 85.0) / 35.0)
    else:
        vvix_proxy = clamp01(0.45 * vix_level + 0.35 * iv_premium + 0.20 * narrow_leadership)

    if np.isfinite(skew_last):
        skew_proxy = clamp01((skew_last - 115.0) / 25.0)
    else:
        skew_proxy = clamp01(0.45 * iv_premium + 0.25 * narrow_leadership + 0.30 * max(0.0, vix_level - 0.35))

    if np.isfinite(vix3m_last) and np.isfinite(vix_last) and vix3m_last > 1e-9:
        term_structure_proxy = clamp01((vix_last / vix3m_last - 0.90) / 0.30)
    else:
        term_structure_proxy = clamp01(0.35 * vix_level + 0.35 * vix_trend + 0.30 * iv_premium)

    vol_of_vol_proxy = clamp01(0.55 * vvix_proxy + 0.25 * vix_trend + 0.20 * narrow_leadership)
    tail_hedge_bid = clamp01(0.40 * iv_premium + 0.30 * skew_proxy + 0.30 * vol_of_vol_proxy)

    vol_stress = _weighted_mean(
        {
            "vix_level": vix_level,
            "vix_trend": vix_trend,
            "iv_premium": iv_premium,
            "vol_of_vol": vol_of_vol_proxy,
            "tail_hedge_bid": tail_hedge_bid,
        },
        DERIVATIVES_VOL_WEIGHTS,
    )

    if vol_stress >= 0.70:
        vol_regime = "high"
    elif vol_stress >= 0.55:
        vol_regime = "elevated"
    elif vol_stress <= 0.35:
        vol_regime = "calm"
    else:
        vol_regime = "normal"

    return {
        "vix_last": 0.0 if not np.isfinite(vix_last) else vix_last,
        "vvix_last": 0.0 if not np.isfinite(vvix_last) else vvix_last,
        "skew_last": 0.0 if not np.isfinite(skew_last) else skew_last,
        "vix3m_last": 0.0 if not np.isfinite(vix3m_last) else vix3m_last,
        "rv20_annualized": rv20,
        "iv_rv_ratio": iv_rv_ratio,
        "iv_premium": iv_premium,
        "vix_level": vix_level,
        "vix_trend": vix_trend,
        "vvix_proxy": vvix_proxy,
        "skew_proxy": skew_proxy,
        "term_structure_proxy": term_structure_proxy,
        "vol_of_vol_proxy": vol_of_vol_proxy,
        "tail_hedge_bid": tail_hedge_bid,
        "vol_stress": vol_stress,
        "vol_regime": vol_regime,
        "is_proxy_only": not (np.isfinite(vvix_last) or np.isfinite(skew_last) or np.isfinite(vix3m_last)),
    }
