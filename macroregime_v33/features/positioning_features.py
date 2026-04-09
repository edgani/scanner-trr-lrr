from __future__ import annotations
from typing import Dict

from config.weights import POSITIONING_PROXY_WEIGHTS
from utils.math_utils import clamp01


def _blend(parts: Dict[str, float], weights: Dict[str, float]) -> float:
    total = sum(max(0.0, float(weights.get(k, 0.0))) for k in parts) or 1.0
    acc = sum(float(parts[k]) * max(0.0, float(weights.get(k, 0.0))) for k in parts)
    return clamp01(acc / total)


def _score_pos(x: float, scale: float) -> float:
    return clamp01(0.5 + float(x) / max(scale, 1e-9))


def build_positioning_features(market: Dict[str, float]) -> Dict[str, float]:
    qqq_rel = float(market.get("qqq_1m", 0.0) - market.get("spy_1m", 0.0))
    rsp_rel = float(market.get("rsp_rel_1m", 0.0))
    iwm_rel = float(market.get("iwm_rel_1m", 0.0))
    sector_ratio = float(market.get("sector_support_ratio", 0.5))
    narrow = float(market.get("narrow_leadership", 0.5))
    dxy_1m = float(market.get("dxy_1m", 0.0))
    vix_1m = float(market.get("vix_1m", 0.0))

    concentration = _score_pos(qqq_rel, 0.06)
    breadth_lag = _score_pos(-rsp_rel, 0.06)
    smallcap_lag = _score_pos(-iwm_rel, 0.08)
    dollar_pressure = _score_pos(dxy_1m, 0.04)
    vol_pressure = _score_pos(vix_1m, 0.20)
    coverage_penalty = clamp01(1.0 - sector_ratio)
    narrow_leadership = clamp01(narrow)

    crowding_proxy = _blend(
        {
            "concentration": concentration,
            "breadth_lag": breadth_lag,
            "smallcap_lag": smallcap_lag,
            "coverage_penalty": coverage_penalty,
            "dollar_pressure": dollar_pressure,
            "vol_pressure": vol_pressure,
            "narrow_leadership": narrow_leadership,
        },
        POSITIONING_PROXY_WEIGHTS,
    )

    unwind_risk_proxy = clamp01(
        0.40 * crowding_proxy
        + 0.20 * breadth_lag
        + 0.15 * smallcap_lag
        + 0.10 * coverage_penalty
        + 0.10 * dollar_pressure
        + 0.05 * narrow_leadership
    )
    squeeze_risk_proxy = clamp01(
        0.35 * crowding_proxy
        + 0.25 * vol_pressure
        + 0.20 * dollar_pressure
        + 0.10 * (1.0 - breadth_lag)
        + 0.10 * (1.0 - smallcap_lag)
    )
    positioning_quality = clamp01(1.0 - 0.75 * crowding_proxy - 0.25 * unwind_risk_proxy)

    if crowding_proxy >= 0.72:
        crowding_state = "crowded_long"
    elif crowding_proxy >= 0.55:
        crowding_state = "elevated"
    else:
        crowding_state = "clean"

    return {
        "crowding_proxy": crowding_proxy,
        "crowding_state": crowding_state,
        "crowding": crowding_proxy,  # backward-compatible alias
        "concentration": concentration,
        "breadth_lag": breadth_lag,
        "smallcap_lag": smallcap_lag,
        "dollar_pressure": dollar_pressure,
        "vol_pressure": vol_pressure,
        "coverage_penalty": coverage_penalty,
        "narrow_leadership": narrow_leadership,
        "positioning_quality": positioning_quality,
        "squeeze_risk_proxy": squeeze_risk_proxy,
        "unwind_risk_proxy": unwind_risk_proxy,
        "squeeze_risk": squeeze_risk_proxy,  # backward-compatible alias
        "unwind_risk": unwind_risk_proxy,    # backward-compatible alias
        "is_proxy_only": True,
    }
