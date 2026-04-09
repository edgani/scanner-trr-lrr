from __future__ import annotations
from typing import Dict
from domain.types import ShockState
from utils.math_utils import clamp01

class ShockOverrideEngine:
    def run(self, scenario_features: Dict[str, object], plumbing: Dict[str, float], vol_credit: Dict[str, float]) -> ShockState:
        oil = float(scenario_features.get("oil_shock", 0.0))
        usd = float(scenario_features.get("usd_pressure", 0.0))
        scf = float(scenario_features.get("small_cap_failure", 0.0))
        vol = float(scenario_features.get("vol_rising", 0.0))
        pressure = 0.30 * oil + 0.25 * usd + 0.20 * scf + 0.25 * vol
        pressure = max(pressure, 0.4 * plumbing.get("long_end_pressure", 0.5) + 0.6 * vol_credit.get("vol_stress", 0.5))
        if pressure >= 0.72:
            state = "shock"
            anchor_relaxation = 0.72
        elif pressure >= 0.58:
            state = "stress"
            anchor_relaxation = 0.50
        elif pressure >= 0.45:
            state = "normal"
            anchor_relaxation = 0.30
        else:
            state = "calm"
            anchor_relaxation = 0.18
        triggers = list(scenario_features.get("flags", []))
        return ShockState(
            state=state,
            override_strength=clamp01(pressure),
            anchor_relaxation=anchor_relaxation,
            triggers=triggers,
        )
