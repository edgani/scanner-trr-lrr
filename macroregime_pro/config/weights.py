from __future__ import annotations

"""Central weight registry.

These registries are intended to be the active source of truth for the engines.
Keep engine-side hardcoded weights to an absolute minimum.
"""

STRUCTURAL_QUAD_CORE_WEIGHTS = {
    "growth_level": 0.35,
    "growth_momentum": 0.25,
    "inflation_level": 0.25,
    "inflation_momentum": 0.15,
    "policy_rate": 0.10,
    "liquidity_impulse": 0.10,
}

MONTHLY_QUAD_CORE_WEIGHTS = {
    "growth_level": 0.20,
    "growth_momentum": 0.45,
    "inflation_level": 0.15,
    "inflation_momentum": 0.45,
    "policy_rate": 0.10,
    "liquidity_impulse": 0.10,
    "inflation_shock": 0.15,
}

QUAD_CORE_WEIGHTS = STRUCTURAL_QUAD_CORE_WEIGHTS

QUAD_MODIFIER_WEIGHTS = {
    "slowdown_to_q2": -0.08,
    "slowdown_to_q3": 0.10,
    "inflation_shock_to_q1": -0.10,
    "inflation_shock_to_q3": 0.08,
    "growth_momentum_to_q2": 0.05,
    "growth_momentum_to_q4": 0.08,
    "coverage_penalty": 0.50,
}

MONTHLY_QUAD_MODIFIER_WEIGHTS = {
    "slowdown_to_q2": -0.06,
    "slowdown_to_q3": 0.12,
    "inflation_shock_to_q1": -0.04,
    "inflation_shock_to_q3": 0.16,
    "growth_momentum_to_q2": 0.04,
    "growth_momentum_to_q4": 0.06,
    "coverage_penalty": 0.55,
}

TACTICAL_TRADE_WEIGHTS = {
    "breadth": 0.35,
    "trade_trend": 0.25,
    "credit": 0.20,
    "vol_calm": 0.20,
}

TACTICAL_TREND_WEIGHTS = {
    "spy_trend": 0.40,
    "eqw_health": 0.20,
    "small_caps": 0.15,
    "sector_support": 0.15,
    "dollar_relief": 0.10,
}

TACTICAL_TAIL_WEIGHTS = {
    "vol_calm": 0.35,
    "credit": 0.25,
    "small_cap_confirm": 0.20,
    "dollar_relief": 0.10,
    "narrow_leadership_relief": 0.10,
}

TACTICAL_AGG_WEIGHTS = {
    "trade": 0.35,
    "trend": 0.35,
    "tail": 0.30,
}

VOL_CREDIT_WEIGHTS = {
    "vix_trend_stress": 0.35,
    "dollar_headwind": 0.20,
    "narrow_leadership": 0.15,
    "credit_trend": 0.20,
    "duration_relief": 0.10,
}

POSITIONING_PROXY_WEIGHTS = {
    "concentration": 0.25,
    "breadth_lag": 0.20,
    "smallcap_lag": 0.15,
    "coverage_penalty": 0.10,
    "dollar_pressure": 0.10,
    "vol_pressure": 0.10,
    "narrow_leadership": 0.10,
}

DERIVATIVES_VOL_WEIGHTS = {
    "vix_level": 0.30,
    "vix_trend": 0.25,
    "iv_premium": 0.20,
    "vol_of_vol": 0.15,
    "tail_hedge_bid": 0.10,
}

EXECUTION_BRIDGE_WEIGHTS = {
    "weather": 0.20,
    "health": 0.14,
    "vix_bucket": 0.10,
    "quad": 0.12,
    "confidence": 0.10,
    "cross_asset": 0.09,
    "crowding_penalty": 0.09,
    "shock_penalty": 0.08,
    "crash_penalty": 0.08,
}

RISK_RANGE_WEIGHTS = {
    "realized_vol": 0.40,
    "dollar_pressure": 0.15,
    "vol_stress": 0.15,
    "crowding": 0.10,
    "shock": 0.10,
    "tail_hedge_bid": 0.10,
}

CRASH_METER_WEIGHTS = {
    "tail_state": 0.16,
    "shock_state": 0.18,
    "health_fragility": 0.12,
    "vix_bucket": 0.14,
    "unwind_risk": 0.14,
    "vol_stress": 0.12,
    "tail_hedge_bid": 0.08,
    "dollar_pressure": 0.06,
}

US_ENGINE_WEIGHTS = {
    "regime": 0.28,
    "breadth_credit_vol": 0.24,
    "sector_style": 0.18,
    "stock_ranking": 0.16,
    "execution": 0.14,
}


IHSG_ENGINE_WEIGHTS = {
    "regime": 0.24,
    "em_rotation": 0.16,
    "macro_native": 0.24,
    "breadth_flow": 0.18,
    "execution": 0.18,
}

FX_ENGINE_WEIGHTS = {
    "regime": 0.20,
    "macro_direction": 0.28,
    "amplifier": 0.18,
    "pair_breadth": 0.14,
    "execution": 0.20,
}

COMMODITY_ENGINE_WEIGHTS = {
    "regime": 0.22,
    "native": 0.34,
    "family_strength": 0.12,
    "execution": 0.16,
    "petrodollar": 0.16,
}

CRYPTO_ENGINE_WEIGHTS = {
    "regime": 0.24,
    "boom": 0.28,
    "fragility_penalty": -0.18,
    "breadth": 0.12,
    "execution": 0.18,
}

ROTATION_ENGINE_WEIGHTS = {
    "structural": 0.55,
    "monthly": 0.45,
}

EM_ROTATION_WEIGHTS = {
    "structural": 0.55,
    "monthly": 0.45,
    "usd_relief": 0.20,
    "broad_em": 0.25,
    "commodity_exporter": 0.20,
    "breadth": 0.20,
    "duration": 0.15,
}

OUTLIER_WEIGHTS = {
    "rel_strength": 0.30,
    "trend_persistence": 0.20,
    "volatility_health": 0.10,
    "narrative_cluster": 0.10,
    "scenario_robustness": 0.20,
    "crowding_penalty": -0.10,
}

# Backward-compatible aliases for modules that still read the old names.
MACRO_FEATURE_WEIGHTS = {
    "growth_level": STRUCTURAL_QUAD_CORE_WEIGHTS["growth_level"],
    "growth_momentum": STRUCTURAL_QUAD_CORE_WEIGHTS["growth_momentum"],
    "inflation_level": STRUCTURAL_QUAD_CORE_WEIGHTS["inflation_level"],
    "inflation_momentum": STRUCTURAL_QUAD_CORE_WEIGHTS["inflation_momentum"],
}

TACTICAL_FEATURE_WEIGHTS = {
    "breadth": TACTICAL_TRADE_WEIGHTS["breadth"],
    "trend": TACTICAL_TREND_WEIGHTS["spy_trend"],
    "small_caps": TACTICAL_TREND_WEIGHTS["small_caps"],
    "credit": TACTICAL_TAIL_WEIGHTS["credit"],
    "dollar": TACTICAL_TREND_WEIGHTS["dollar_relief"],
    "volatility": TACTICAL_TAIL_WEIGHTS["vol_calm"],
}
