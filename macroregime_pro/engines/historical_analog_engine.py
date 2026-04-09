from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List

from domain.types import AnalogCase
from utils.math_utils import clamp01


@dataclass(frozen=True)
class _AnalogTemplate:
    label: str
    vector: Dict[str, float]
    path_1m: str
    path_3m: str
    path_6m: str
    next_bias: str
    expected_duration: str
    scenario_family: str
    impacts: Dict[str, str]


_ANALOG_LIBRARY = [
    _AnalogTemplate(
        label="2018 trade-war pressure",
        vector={"growth": -0.20, "inflation": 0.15, "dollar": 0.40, "oil": 0.05, "smallcap": -0.40, "vol": 0.25, "long_end": 0.10},
        path_1m="policy-sensitive chop",
        path_3m="narrow leaders and defensive bid",
        path_6m="relief possible after moderation",
        next_bias="Monthly pressure may fade, structural slowdown stays",
        expected_duration="3-8 weeks",
        scenario_family="policy_pressure",
        impacts={"us": "mixed", "ihsg": "bearish", "fx": "bullish_usd", "commodities": "mixed", "crypto": "bearish"},
    ),
    _AnalogTemplate(
        label="2022 commodity shock",
        vector={"growth": -0.35, "inflation": 0.75, "dollar": 0.20, "oil": 0.90, "smallcap": -0.35, "vol": 0.50, "long_end": 0.20},
        path_1m="inflation scare and resource lead",
        path_3m="dispersion with fragile beta",
        path_6m="policy threshold eventually matters",
        next_bias="Monthly Q3 can persist while structural pressure broadens",
        expected_duration="4-10 weeks",
        scenario_family="commodity_shock",
        impacts={"us": "energy_up_beta_fragile", "ihsg": "exporters_up_importers_down", "fx": "commodity_fx_up", "commodities": "bullish", "crypto": "mixed_to_bearish"},
    ),
    _AnalogTemplate(
        label="2025 tariff bond rout",
        vector={"growth": -0.25, "inflation": 0.30, "dollar": 0.50, "oil": 0.10, "smallcap": -0.55, "vol": 0.45, "long_end": 0.80},
        path_1m="long-end pain and broad stress",
        path_3m="negotiation relief can squeeze laggards",
        path_6m="outcome hinges on de-escalation",
        next_bias="Structural stress dominates unless policy relief lands",
        expected_duration="2-6 weeks",
        scenario_family="rates_shock",
        impacts={"us": "defensive", "ihsg": "bearish", "fx": "usd_up", "commodities": "gold_over_cyclicals", "crypto": "bearish"},
    ),
    _AnalogTemplate(
        label="2026 war-oil stagflation",
        vector={"growth": -0.30, "inflation": 0.80, "dollar": 0.35, "oil": 0.95, "smallcap": -0.45, "vol": 0.55, "long_end": 0.60},
        path_1m="oil-first stagflation pressure",
        path_3m="energy lead with mixed broader tape",
        path_6m="de-escalation can abruptly rotate leadership",
        next_bias="Petrodollar branch can keep monthly Q3 alive inside structural slowdown",
        expected_duration="2-8 weeks",
        scenario_family="petrodollar_tightening",
        impacts={"us": "energy_vs_cyclicals", "ihsg": "coal_up_rupiah_fragile", "fx": "usd_and_petrocurrency_bid", "commodities": "energy_gold_up", "crypto": "fragile"},
    ),
    _AnalogTemplate(
        label="mid-cycle mixed slowdown",
        vector={"growth": -0.05, "inflation": 0.05, "dollar": 0.00, "oil": 0.00, "smallcap": -0.05, "vol": 0.10, "long_end": 0.10},
        path_1m="rotation without panic",
        path_3m="slowdown signs but no crash",
        path_6m="macro path decides winners",
        next_bias="Base case stays mixed until a cleaner impulse emerges",
        expected_duration="4-12 weeks",
        scenario_family="mixed_slowdown",
        impacts={"us": "mixed", "ihsg": "mixed", "fx": "range", "commodities": "selective", "crypto": "selective"},
    ),
]


class HistoricalAnalogEngine:
    def run(self, macro: Dict[str, float], market: Dict[str, float], shock_state: str) -> List[AnalogCase]:
        state = {
            "growth": float(0.55 * macro.get("growth_level", 0.0) + 0.45 * macro.get("growth_momentum", 0.0)),
            "inflation": float(0.55 * macro.get("inflation_level", 0.0) + 0.45 * macro.get("inflation_momentum", 0.0)),
            "dollar": float(market.get("dxy_1m", 0.0)),
            "oil": float(macro.get("oil_3m", 0.0)),
            "smallcap": float(market.get("iwm_rel_1m", 0.0)),
            "vol": float(market.get("vix_1m", 0.0)),
            "long_end": float(max(0.0, -market.get("tlt_1m", 0.0))),
        }

        ranked = []
        for analog in _ANALOG_LIBRARY:
            distance = 0.0
            for k, v in analog.vector.items():
                distance += (state.get(k, 0.0) - v) ** 2
            distance = distance ** 0.5
            similarity = clamp01(1.0 - distance / 2.2)
            if shock_state == "shock" and "shock" in analog.label.lower():
                similarity = clamp01(similarity + 0.04)
            if state["long_end"] > 0.45 and "bond rout" in analog.label.lower():
                similarity = clamp01(similarity + 0.05)
            conf_adj = round((similarity - 0.5) * 0.10, 4)
            ranked.append(
                AnalogCase(
                    label=analog.label,
                    similarity=similarity,
                    path_1m=analog.path_1m,
                    path_3m=analog.path_3m,
                    path_6m=analog.path_6m,
                    next_bias=analog.next_bias,
                    expected_duration=analog.expected_duration,
                    confidence_adjustment=conf_adj,
                    scenario_family=analog.scenario_family,
                    impacts=analog.impacts,
                )
            )

        ranked.sort(key=lambda x: x.similarity, reverse=True)
        return ranked[:3]
