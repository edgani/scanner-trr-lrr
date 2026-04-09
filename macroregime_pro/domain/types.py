from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class RegimePosterior:
    probs: Dict[str, float]
    current_quad: str
    next_quad: str
    confidence: float
    deepness: float
    duration_maturity: float
    flip_hazard: float
    g_core: float = 0.0
    i_core: float = 0.0
    p_core: float = 0.0
    prior_mode: str = "off"
    prior_strength: float = 0.0
    coverage_penalty: float = 0.0
    structural_quad: str = "Q?"
    structural_next_quad: str = "Q?"
    structural_probs: Dict[str, float] = field(default_factory=dict)
    structural_confidence: float = 0.0
    monthly_quad: str = "Q?"
    monthly_next_quad: str = "Q?"
    monthly_probs: Dict[str, float] = field(default_factory=dict)
    monthly_confidence: float = 0.0
    g_monthly_core: float = 0.0
    i_monthly_core: float = 0.0
    p_monthly_core: float = 0.0
    divergence_state: str = "unknown"
    operating_regime: str = "unknown"

@dataclass
class TacticalState:
    weather_bias: str
    trade_state: str
    trend_state: str
    tail_state: str
    score: float
    cross_asset_confirm: float
    trade_score: float = 0.5
    trend_score: float = 0.5
    tail_score: float = 0.5

@dataclass
class ShockState:
    state: str
    override_strength: float
    anchor_relaxation: float
    triggers: List[str] = field(default_factory=list)

@dataclass
class ScenarioCase:
    name: str
    probability: float
    description: str
    invalidators: List[str] = field(default_factory=list)
    winners: List[str] = field(default_factory=list)
    losers: List[str] = field(default_factory=list)

@dataclass
class OutlierCandidate:
    symbol: str
    score: float
    category: str
    reasons: List[str] = field(default_factory=list)

@dataclass
class AnalogCase:
    label: str
    similarity: float
    path_1m: str
    path_3m: str
    path_6m: str
    next_bias: str = "mixed"
    expected_duration: str = "4-8 weeks"
    confidence_adjustment: float = 0.0
    scenario_family: str = "base"
    impacts: Dict[str, str] = field(default_factory=dict)
