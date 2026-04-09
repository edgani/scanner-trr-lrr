from __future__ import annotations
from typing import Dict

from config.weights import TACTICAL_AGG_WEIGHTS, TACTICAL_TAIL_WEIGHTS, TACTICAL_TRADE_WEIGHTS, TACTICAL_TREND_WEIGHTS
from domain.types import TacticalState
from utils.math_utils import clamp01


class TacticalWeatherEngine:
    def run(self, market: Dict[str, float], breadth: Dict[str, float], vol_credit: Dict[str, float]) -> TacticalState:
        trade_score = clamp01(
            TACTICAL_TRADE_WEIGHTS["breadth"] * breadth.get("breadth_score", 0.5)
            + TACTICAL_TRADE_WEIGHTS["trade_trend"] * market.get("spy_trend", 0.5)
            + TACTICAL_TRADE_WEIGHTS["credit"] * vol_credit.get("credit_health", 0.5)
            + TACTICAL_TRADE_WEIGHTS["vol_calm"] * (1.0 - vol_credit.get("vol_stress", 0.5))
        )

        trend_score = clamp01(
            TACTICAL_TREND_WEIGHTS["spy_trend"] * market.get("spy_trend", 0.5)
            + TACTICAL_TREND_WEIGHTS["eqw_health"] * market.get("eqw_health", breadth.get("breadth_score", 0.5))
            + TACTICAL_TREND_WEIGHTS["small_caps"] * market.get("smallcap_health", breadth.get("small_cap_confirm", 0.5))
            + TACTICAL_TREND_WEIGHTS["sector_support"] * breadth.get("sector_support_ratio", 0.5)
            + TACTICAL_TREND_WEIGHTS["dollar_relief"] * (0.5 - market.get("dxy_1m", 0.0))
        )

        tail_score = clamp01(
            TACTICAL_TAIL_WEIGHTS["vol_calm"] * (1.0 - vol_credit.get("vol_stress", 0.5))
            + TACTICAL_TAIL_WEIGHTS["credit"] * vol_credit.get("credit_health", 0.5)
            + TACTICAL_TAIL_WEIGHTS["small_cap_confirm"] * breadth.get("small_cap_confirm", 0.5)
            + TACTICAL_TAIL_WEIGHTS["dollar_relief"] * (0.5 - market.get("dxy_1m", 0.0))
            + TACTICAL_TAIL_WEIGHTS["narrow_leadership_relief"] * (1.0 - breadth.get("narrow_leadership", 0.5))
        )

        score = clamp01(
            TACTICAL_AGG_WEIGHTS["trade"] * trade_score
            + TACTICAL_AGG_WEIGHTS["trend"] * trend_score
            + TACTICAL_AGG_WEIGHTS["tail"] * tail_score
        )

        weather_bias = "risk_on" if score >= 0.58 else ("risk_off" if score <= 0.42 else "mixed")
        trade_state = "supportive" if trade_score >= 0.60 else ("hostile" if trade_score <= 0.40 else "balanced")
        trend_state = "persistent" if trend_score >= 0.60 else ("fragile" if trend_score <= 0.40 else "mixed")
        tail_state = "calm" if tail_score >= 0.58 else ("stressed" if tail_score <= 0.42 else "neutral")
        cross_asset_confirm = clamp01(0.40 * breadth.get("small_cap_confirm", 0.5) + 0.30 * vol_credit.get("credit_health", 0.5) + 0.30 * (0.5 - market.get("dxy_1m", 0.0)))

        return TacticalState(
            weather_bias=weather_bias,
            trade_state=trade_state,
            trend_state=trend_state,
            tail_state=tail_state,
            score=score,
            cross_asset_confirm=cross_asset_confirm,
            trade_score=trade_score,
            trend_score=trend_score,
            tail_score=tail_score,
        )
