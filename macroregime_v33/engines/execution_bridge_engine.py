from __future__ import annotations
from typing import Dict

from config.weights import EXECUTION_BRIDGE_WEIGHTS
from utils.math_utils import clamp01 as _clamp01


def _quad_score(quad: str) -> float:
    return {
        "Q1": 0.68,
        "Q2": 0.78,
        "Q3": 0.48,
        "Q4": 0.25,
    }.get(str(quad), 0.50)


def _health_score(verdict: str) -> float:
    return {
        "Healthy": 0.80,
        "Constructive": 0.68,
        "Narrow": 0.48,
        "Fragile": 0.34,
        "Broken": 0.18,
    }.get(str(verdict), 0.50)


def _bucket_score(bucket: str) -> float:
    return {
        "Calm": 0.78,
        "Normal": 0.62,
        "Elevated": 0.42,
        "Stress": 0.22,
        "Unknown": 0.50,
    }.get(str(bucket), 0.50)


class ExecutionBridgeEngine:
    def run(
        self,
        structural: Dict[str, object],
        tactical: Dict[str, object],
        shock: Dict[str, object],
        market_health: Dict[str, object],
        vix_bucket: Dict[str, object],
        positioning: Dict[str, object],
        derivatives: Dict[str, object] | None = None,
    ) -> Dict[str, object]:
        derivatives = derivatives or {}

        structural_quad = str(structural.get('structural_quad', structural.get('current_quad', 'Q3')))
        monthly_quad = str(structural.get('monthly_quad', structural_quad))
        divergence = str(structural.get('divergence_state', 'aligned' if structural_quad == monthly_quad else 'divergent'))
        quad_conf = _clamp01(structural.get('structural_confidence', structural.get('confidence', 0.5)))
        monthly_conf = _clamp01(structural.get('monthly_confidence', quad_conf))

        weather = str(tactical.get('weather_bias', 'mixed'))
        weather_score = _clamp01(tactical.get('score', 0.5))
        cross_asset_confirm = _clamp01(tactical.get('cross_asset_confirm', 0.5))
        trade_state = str(tactical.get('trade_state', 'balanced'))
        tail_state = str(tactical.get('tail_state', 'neutral'))
        shock_state = str(shock.get('state', 'normal'))
        health = str(market_health.get('verdict', 'Narrow'))
        bucket = str(vix_bucket.get('bucket', 'Unknown'))
        crowding = _clamp01(positioning.get('crowding_proxy', positioning.get('crowding', 0.5)))
        unwind_risk = _clamp01(positioning.get('unwind_risk_proxy', positioning.get('unwind_risk', 0.5)))
        deriv_stress = _clamp01(derivatives.get('vol_stress', 0.5))
        tail_hedge_bid = _clamp01(derivatives.get('tail_hedge_bid', 0.5))

        health_component = _health_score(health)
        bucket_component = _bucket_score(bucket)
        structural_component = _quad_score(structural_quad)
        monthly_component = _quad_score(monthly_quad)

        if divergence == 'aligned':
            divergence_adjustment = 0.08 * max(0.0, cross_asset_confirm - 0.5)
        else:
            if weather_score >= 0.58 and trade_state == 'supportive' and tail_state != 'stressed':
                divergence_adjustment = 0.06 * max(0.0, monthly_component - structural_component)
            elif weather_score <= 0.42 or tail_state == 'stressed':
                divergence_adjustment = -0.06 * max(0.0, monthly_component - structural_component)
            else:
                divergence_adjustment = -0.03 * abs(monthly_component - structural_component)

        shock_penalty = 1.0 if shock_state == 'shock' else 0.70 if shock_state == 'stress' else 0.20 if shock_state == 'watch' else 0.0
        crowding_penalty = _clamp01(0.65 * crowding + 0.35 * unwind_risk)
        crash_penalty = _clamp01(max(0.0, 0.55 * deriv_stress + 0.25 * tail_hedge_bid + 0.20 * unwind_risk - 0.30))

        blended_quad = 0.65 * structural_component + 0.35 * monthly_component
        blended_conf = 0.60 * quad_conf + 0.40 * monthly_conf

        score = 0.50
        score += EXECUTION_BRIDGE_WEIGHTS["weather"] * (weather_score - 0.5)
        score += EXECUTION_BRIDGE_WEIGHTS["health"] * (health_component - 0.5)
        score += EXECUTION_BRIDGE_WEIGHTS["vix_bucket"] * (bucket_component - 0.5)
        score += EXECUTION_BRIDGE_WEIGHTS["quad"] * (blended_quad - 0.5)
        score += EXECUTION_BRIDGE_WEIGHTS["confidence"] * (blended_conf - 0.5)
        score += EXECUTION_BRIDGE_WEIGHTS["cross_asset"] * (cross_asset_confirm - 0.5)
        score += divergence_adjustment
        score -= EXECUTION_BRIDGE_WEIGHTS["crowding_penalty"] * crowding_penalty
        score -= EXECUTION_BRIDGE_WEIGHTS["shock_penalty"] * shock_penalty
        score -= EXECUTION_BRIDGE_WEIGHTS["crash_penalty"] * crash_penalty
        score = _clamp01(score)

        if score >= 0.70:
            mode = "aggressive"
            execute_mode = "Aggressive buy-the-dip / hold winners"
            size_mult = 1.00
        elif score >= 0.56:
            mode = "normal"
            execute_mode = "Normal risk / selective adds"
            size_mult = 0.75
        elif score >= 0.42:
            mode = "reduced"
            execute_mode = "Reduced risk / quick trades only"
            size_mult = 0.50
        else:
            mode = "defensive"
            execute_mode = "Defensive / preserve capital"
            size_mult = 0.25

        can_chase = bool(score >= 0.68 and shock_penalty < 0.70 and crowding_penalty < 0.62 and crash_penalty < 0.45)
        buy_dip_only = bool(score >= 0.52 and not can_chase)
        breakout_only = bool(weather_score >= 0.58 and cross_asset_confirm >= 0.56 and crowding_penalty < 0.72 and crash_penalty < 0.55)
        reduce_on_strength = bool(crowding_penalty >= 0.65 or crash_penalty >= 0.55 or shock_penalty >= 0.70)
        short_bounces_only = bool(score <= 0.44 or (weather_score <= 0.42 and crash_penalty >= 0.45))
        no_trade = bool(score <= 0.32 or (shock_penalty >= 0.90 and crash_penalty >= 0.62))

        if no_trade:
            execute_mode = 'No-trade / preserve capital'
            mode = 'no_trade'
            size_mult = 0.10

        notes = [
            f"Structural {structural_quad} / Monthly {monthly_quad} ({divergence}) + weather {weather} + VIX bucket {bucket}.",
            f"Market health: {health}; shock state: {shock_state}; cross-asset confirm {cross_asset_confirm:.2f}.",
        ]
        if divergence == 'divergent':
            notes.append('Execution bias now depends on whether signal confirms the monthly move or hands control back to the structural regime.')
        if crowding_penalty >= 0.65:
            notes.append("Crowding / unwind risk tinggi; lebih disiplin saat tambah risk.")
        if crash_penalty >= 0.55:
            notes.append("Crash-cascade penalty naik; prioritaskan capital preservation dan liquidity.")

        return {
            "score": score,
            "mode": mode,
            "execute_mode": execute_mode,
            "size_multiplier": size_mult,
            "score_components": {
                "weather": weather_score,
                "health": health_component,
                "vix_bucket": bucket_component,
                "structural_quad": structural_component,
                "monthly_quad": monthly_component,
                "blended_quad": blended_quad,
                "confidence": blended_conf,
                "cross_asset": cross_asset_confirm,
                "divergence_adjustment": divergence_adjustment,
                "crowding_penalty": crowding_penalty,
                "shock_penalty": shock_penalty,
                "crash_penalty": crash_penalty,
            },
            "flags": {
                "can_chase": can_chase,
                "buy_dip_only": buy_dip_only,
                "breakout_only": breakout_only,
                "reduce_on_strength": reduce_on_strength,
                "short_bounces_only": short_bounces_only,
                "no_trade": no_trade,
            },
            "notes": notes,
        }
