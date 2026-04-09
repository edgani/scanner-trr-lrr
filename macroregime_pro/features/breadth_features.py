from __future__ import annotations
from typing import Dict

import numpy as np


def build_breadth_features(market: Dict[str, float]) -> Dict[str, float]:
    breadth_components = [
        market.get("breadth_health", 0.5),
        market.get("eqw_health", 0.5),
        market.get("smallcap_health", 0.5),
        market.get("sector_support_ratio", 0.5),
    ]
    breadth_score = float(np.nanmean(breadth_components))
    return {
        "breadth_score": max(0.0, min(1.0, breadth_score)),
        "small_cap_confirm": max(0.0, min(1.0, float(market.get("smallcap_health", 0.5)))),
        "sector_support_ratio": max(0.0, min(1.0, float(market.get("sector_support_ratio", 0.5)))),
        "narrow_leadership": max(0.0, min(1.0, float(market.get("narrow_leadership", 0.5)))),
    }
