from __future__ import annotations
from typing import Dict, Tuple

from config.settings import REGIME_PRIOR_MODE, get_prior_strength, get_regime_prior
from config.weights import (
    MONTHLY_QUAD_CORE_WEIGHTS,
    MONTHLY_QUAD_MODIFIER_WEIGHTS,
    QUAD_CORE_WEIGHTS,
    QUAD_MODIFIER_WEIGHTS,
)
from domain.types import RegimePosterior
from utils.math_utils import clamp01, softmax_dict


class QuadStateEngine:
    """Dual-horizon quad engine.

    Structural quad = slower dominant regime.
    Monthly quad    = faster weather overlay inside the structural backdrop.
    For backward compatibility, `current_quad` remains the structural quad.
    """

    def _score_block(
        self,
        *,
        g_level: float,
        g_mom: float,
        i_level: float,
        i_mom: float,
        policy_score: float,
        liquidity_score: float,
        slowdown_flags: float,
        inflation_shock: float,
        data_coverage: float,
        macro_proxy_share: float,
        core_w: Dict[str, float],
        mod_w: Dict[str, float],
        monthly: bool = False,
    ) -> Tuple[Dict[str, float], str, str, float, float, float, float]:
        g_core = core_w["growth_level"] * g_level + core_w["growth_momentum"] * g_mom
        i_core = core_w["inflation_level"] * i_level + core_w["inflation_momentum"] * i_mom
        p_core = core_w["policy_rate"] * policy_score + core_w["liquidity_impulse"] * liquidity_score
        if monthly:
            i_core += core_w.get("inflation_shock", 0.0) * max(0.0, inflation_shock)

        raw = {
            "Q1": +g_core - i_core - (0.10 if monthly else 0.20) * p_core,
            "Q2": +g_core + i_core - (0.05 if monthly else 0.10) * p_core,
            "Q3": -g_core + (1.10 if monthly else 1.00) * i_core + 0.05 * p_core,
            "Q4": -g_core - (0.90 if monthly else 1.00) * i_core + (0.18 if monthly else 0.25) * p_core,
        }
        raw["Q1"] += mod_w["inflation_shock_to_q1"] * max(0.0, inflation_shock)
        raw["Q2"] += mod_w["growth_momentum_to_q2"] * max(0.0, g_mom)
        raw["Q2"] += mod_w["slowdown_to_q2"] * slowdown_flags
        raw["Q3"] += mod_w["slowdown_to_q3"] * slowdown_flags
        raw["Q3"] += mod_w["inflation_shock_to_q3"] * max(0.0, inflation_shock)
        raw["Q4"] += mod_w["growth_momentum_to_q4"] * max(0.0, -g_mom)

        prior_strength = get_prior_strength(data_coverage, REGIME_PRIOR_MODE)
        prior_map = get_regime_prior(REGIME_PRIOR_MODE)
        prior_adjusted = {k: raw[k] + prior_strength * prior_map[k] for k in raw}
        probs = softmax_dict(prior_adjusted)
        ordered = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
        current_quad, top_prob = ordered[0]
        next_quad, next_prob = ordered[1]
        margin = top_prob - next_prob
        coverage_penalty = mod_w["coverage_penalty"] * macro_proxy_share
        confidence = clamp01(top_prob * (0.70 + 0.30 * data_coverage) * (1.0 - coverage_penalty))
        return probs, current_quad, next_quad, confidence, g_core, i_core, p_core

    def run(self, macro: Dict[str, float]) -> RegimePosterior:
        slowdown_flags = float(macro.get("slowdown_flags", 0.0))
        inflation_shock = float(macro.get("inflation_shock", 0.0))
        data_coverage = float(macro.get("data_coverage", 0.75))
        macro_proxy_share = float(macro.get("macro_proxy_share", 0.0))

        structural_probs, structural_quad, structural_next, structural_confidence, g_core, i_core, p_core = self._score_block(
            g_level=float(macro.get("growth_structural_level", macro.get("growth_level", 0.0))),
            g_mom=float(macro.get("growth_structural_momentum", macro.get("growth_momentum", 0.0))),
            i_level=float(macro.get("inflation_structural_level", macro.get("inflation_level", 0.0))),
            i_mom=float(macro.get("inflation_structural_momentum", macro.get("inflation_momentum", 0.0))),
            policy_score=float(macro.get("policy_score", 0.0)),
            liquidity_score=float(macro.get("liquidity_score", 0.0)),
            slowdown_flags=slowdown_flags,
            inflation_shock=inflation_shock,
            data_coverage=data_coverage,
            macro_proxy_share=macro_proxy_share,
            core_w=QUAD_CORE_WEIGHTS,
            mod_w=QUAD_MODIFIER_WEIGHTS,
            monthly=False,
        )

        monthly_probs, monthly_quad, monthly_next, monthly_confidence, g_month, i_month, p_month = self._score_block(
            g_level=float(macro.get("growth_monthly_level", macro.get("growth_level", 0.0))),
            g_mom=float(macro.get("growth_monthly_momentum", macro.get("growth_momentum", 0.0))),
            i_level=float(macro.get("inflation_monthly_level", macro.get("inflation_level", 0.0))),
            i_mom=float(macro.get("inflation_monthly_momentum", macro.get("inflation_momentum", 0.0))),
            policy_score=float(macro.get("monthly_policy_score", macro.get("policy_score", 0.0))),
            liquidity_score=float(macro.get("monthly_liquidity_score", macro.get("liquidity_score", 0.0))),
            slowdown_flags=slowdown_flags,
            inflation_shock=float(macro.get("monthly_inflation_shock", inflation_shock)),
            data_coverage=data_coverage,
            macro_proxy_share=macro_proxy_share,
            core_w=MONTHLY_QUAD_CORE_WEIGHTS,
            mod_w=MONTHLY_QUAD_MODIFIER_WEIGHTS,
            monthly=True,
        )

        if structural_quad == monthly_quad:
            divergence_state = "aligned"
            operating_regime = f"Aligned {structural_quad}"
        else:
            divergence_state = "divergent"
            operating_regime = f"Monthly {monthly_quad} inside Structural {structural_quad}"

        structural_ordered = sorted(structural_probs.items(), key=lambda kv: kv[1], reverse=True)
        margin = structural_ordered[0][1] - structural_ordered[1][1]
        deepness = clamp01((abs(g_core) + abs(i_core) + 0.35 * abs(p_core) + 0.25 * slowdown_flags + 0.20 * max(0.0, inflation_shock)) / 1.8)
        duration_maturity = clamp01(0.30 + 0.35 * deepness + 0.20 * abs(macro.get("inflation_structural_momentum", macro.get("inflation_momentum", 0.0))) + 0.15 * abs(macro.get("growth_structural_momentum", macro.get("growth_momentum", 0.0))))
        disagreement = clamp01(0.5 + 0.5 * abs(g_core - i_core) - 0.5 * margin)
        flip_hazard = clamp01(
            0.30 * (1.0 - margin)
            + 0.20 * duration_maturity
            + 0.15 * disagreement
            + 0.15 * abs(structural_probs.get("Q3", 0.0) - monthly_probs.get("Q3", 0.0))
            + 0.10 * slowdown_flags
            + 0.10 * max(0.0, inflation_shock)
        )

        prior_strength = get_prior_strength(data_coverage, REGIME_PRIOR_MODE)
        coverage_penalty = QUAD_MODIFIER_WEIGHTS["coverage_penalty"] * macro_proxy_share

        return RegimePosterior(
            probs=structural_probs,
            current_quad=structural_quad,
            next_quad=structural_next,
            confidence=structural_confidence,
            deepness=deepness,
            duration_maturity=duration_maturity,
            flip_hazard=flip_hazard,
            g_core=g_core,
            i_core=i_core,
            p_core=p_core,
            prior_mode=REGIME_PRIOR_MODE,
            prior_strength=prior_strength,
            coverage_penalty=coverage_penalty,
            structural_quad=structural_quad,
            structural_next_quad=structural_next,
            structural_probs=structural_probs,
            structural_confidence=structural_confidence,
            monthly_quad=monthly_quad,
            monthly_next_quad=monthly_next,
            monthly_probs=monthly_probs,
            monthly_confidence=monthly_confidence,
            g_monthly_core=g_month,
            i_monthly_core=i_month,
            p_monthly_core=p_month,
            divergence_state=divergence_state,
            operating_regime=operating_regime,
        )
