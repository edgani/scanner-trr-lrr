from __future__ import annotations
from typing import Dict

def build_plumbing_features(macro: Dict[str, float], market: Dict[str, float]) -> Dict[str, float]:
    long_end_pressure = max(0.0, min(1.0, 0.5 - market.get("tlt_1m", 0.0)))
    dollar_pressure = max(0.0, min(1.0, 0.5 + market.get("dxy_1m", 0.0)))
    oil_pressure = max(0.0, min(1.0, 0.5 + macro.get("oil_3m", 0.0)))
    return {
        "long_end_pressure": long_end_pressure,
        "dollar_pressure": dollar_pressure,
        "oil_pressure": oil_pressure,
    }
