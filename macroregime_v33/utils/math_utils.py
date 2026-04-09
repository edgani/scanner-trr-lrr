from __future__ import annotations
import math
from typing import Dict

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

def softmax_dict(values: Dict[str, float]) -> Dict[str, float]:
    if not values:
        return {}
    m = max(values.values())
    exps = {k: math.exp(v - m) for k, v in values.items()}
    s = sum(exps.values()) or 1.0
    return {k: exps[k] / s for k in values}

def normalize_dict(values: Dict[str, float]) -> Dict[str, float]:
    if not values:
        return {}
    total = sum(max(0.0, v) for v in values.values()) or 1.0
    return {k: max(0.0, v) / total for k, v in values.items()}
