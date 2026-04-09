from __future__ import annotations
from typing import Dict

from config.weights import VOL_CREDIT_WEIGHTS
from utils.math_utils import clamp01


def _score_pos(x: float, scale: float) -> float:
    return clamp01(0.5 + float(x) / max(scale, 1e-9))


def _blend(parts: Dict[str, float], weights: Dict[str, float]) -> float:
    total = sum(max(0.0, float(weights.get(k, 0.0))) for k in parts) or 1.0
    acc = sum(float(parts[k]) * max(0.0, float(weights.get(k, 0.0))) for k in parts)
    return clamp01(acc / total)


def build_vol_credit_features(market: Dict[str, float]) -> Dict[str, float]:
    vix_trend_stress = _score_pos(market.get("vix_1m", 0.0), 0.20)
    credit_trend = _score_pos(market.get("hyg_1m", 0.0), 0.06)
    duration_relief = _score_pos(market.get("tlt_1m", 0.0), 0.05)
    dollar_headwind = _score_pos(market.get("dxy_1m", 0.0), 0.04)
    narrow_leadership_stress = clamp01(market.get("narrow_leadership", 0.5))

    vol_stress = _blend(
        {
            "vix_trend_stress": vix_trend_stress,
            "dollar_headwind": dollar_headwind,
            "narrow_leadership": narrow_leadership_stress,
            "credit_trend": 1.0 - credit_trend,
            "duration_relief": 1.0 - duration_relief,
        },
        VOL_CREDIT_WEIGHTS,
    )

    credit_health = clamp01(
        0.45 * credit_trend
        + 0.20 * duration_relief
        + 0.20 * (1.0 - dollar_headwind)
        + 0.15 * (1.0 - narrow_leadership_stress)
    )
    credit_stress = clamp01(1.0 - credit_health)

    tail_hedge_bid = clamp01(
        0.40 * vix_trend_stress
        + 0.25 * dollar_headwind
        + 0.20 * narrow_leadership_stress
        + 0.15 * credit_stress
    )

    if vol_stress >= 0.67:
        vol_regime = "high"
    elif vol_stress >= 0.52:
        vol_regime = "elevated"
    elif vol_stress <= 0.35:
        vol_regime = "calm"
    else:
        vol_regime = "normal"

    if credit_health >= 0.62:
        credit_regime = "easy"
    elif credit_health <= 0.40:
        credit_regime = "tight"
    else:
        credit_regime = "neutral"

    return {
        "vol_stress": vol_stress,
        "credit_health": credit_health,
        "credit_stress": credit_stress,
        "vix_trend_stress": vix_trend_stress,
        "credit_trend": credit_trend,
        "duration_relief": duration_relief,
        "dollar_headwind": dollar_headwind,
        "narrow_leadership_stress": narrow_leadership_stress,
        "tail_hedge_bid": tail_hedge_bid,
        "vol_regime": vol_regime,
        "credit_regime": credit_regime,
    }
