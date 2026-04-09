from __future__ import annotations

from config.asset_buckets import US_BUCKETS, IHSG_BUCKETS, COMMODITY_BUCKETS, CRYPTO_BUCKETS
from utils.math_utils import clamp01


def _risk_terms(shared_core: dict) -> dict:
    risk = shared_core.get("risk_summary", {}) or {}
    return {
        "risk_off_penalty": clamp01(float(risk.get("risk_off_score", 0.0) or 0.0) / 4.0),
        "crash_penalty": clamp01(float(risk.get("crash_score", 0.0) or 0.0) / 6.0),
    }


def _status_terms(shared_core: dict, regime_score: float, breadth_score: float, execution_score: float) -> dict:
    base = _risk_terms(shared_core)
    base.update({
        "regime_score": clamp01(regime_score),
        "breadth_score": clamp01(breadth_score),
        "execution_score": clamp01(execution_score),
    })
    return base


def _add_boosts(boosts: dict[str, float], symbols: list[str], boost: float) -> None:
    for sym in symbols:
        boosts[sym] = boosts.get(sym, 0.0) + boost


def us_ranking_context(shared_core: dict, features: dict | None = None) -> dict:
    features = features or {}
    ribbon = shared_core.get("status_ribbon", {}) or {}
    breadth = clamp01(features.get("breadth_health", shared_core.get("breadth_snapshot", {}).get("breadth_score", 0.5)))
    execution = clamp01(features.get("execution_state", {}).get("score", shared_core.get("execution_mode", {}).get("score", 0.5)))
    structural = str(ribbon.get("structural_quad", "Q3"))
    monthly = str(ribbon.get("monthly_quad", structural))
    regime_map = {"Q1": 0.70, "Q2": 0.78, "Q3": 0.48, "Q4": 0.32}
    regime = 0.6 * regime_map.get(structural, 0.5) + 0.4 * regime_map.get(monthly, 0.5)
    ctx = _status_terms(shared_core, regime, breadth, execution)
    boosts: dict[str, float] = {}
    risk_off = ctx["risk_off_penalty"]
    if monthly in {"Q1", "Q2"} and risk_off < 0.45:
        _add_boosts(boosts, US_BUCKETS.get("Growth", []) + US_BUCKETS.get("Semis", []) + US_BUCKETS.get("Software/Cyber", []), 0.025)
        _add_boosts(boosts, ["PLTR", "ANET", "ARM", "ASML", "BKNG", "RDDT", "UBER"], 0.020)
    if structural in {"Q3", "Q4"} or risk_off > 0.55:
        _add_boosts(boosts, US_BUCKETS.get("Defensives", []) + US_BUCKETS.get("Quality", []), 0.020)
        _add_boosts(boosts, US_BUCKETS.get("Energy", []), 0.015)
    ctx["theme_boosts"] = boosts
    return ctx


def ihsg_ranking_context(shared_core: dict, features: dict | None = None) -> dict:
    features = features or {}
    ribbon = shared_core.get("status_ribbon", {}) or {}
    breadth = clamp01(features.get("breadth_liquidity", shared_core.get("breadth_snapshot", {}).get("breadth_score", 0.5)))
    execution = clamp01(features.get("execution_state", {}).get("score", 0.5))
    structural = str(ribbon.get("structural_quad", "Q3"))
    monthly = str(ribbon.get("monthly_quad", structural))
    regime_map_struct = {"Q1": 0.60, "Q2": 0.68, "Q3": 0.58, "Q4": 0.36}
    regime_map_month = {"Q1": 0.56, "Q2": 0.66, "Q3": 0.66, "Q4": 0.34}
    regime = 0.6 * regime_map_struct.get(structural, 0.5) + 0.4 * regime_map_month.get(monthly, 0.5)
    ctx = _status_terms(shared_core, regime, breadth, execution)
    boosts: dict[str, float] = {}
    foreign_flow = clamp01(features.get("foreign_flow", 0.5))
    commodity_spillover = clamp01(features.get("commodity_spillover", 0.5))
    usd_pressure = clamp01(features.get("usd_idr_pressure", 0.5))
    em_score = clamp01(shared_core.get("em_rotation", {}).get("resolved_score", shared_core.get("em_rotation", {}).get("score", 0.4)))
    catalyst_on = em_score > 0.50 and foreign_flow > 0.48 and ctx["risk_off_penalty"] < 0.60
    if catalyst_on:
        _add_boosts(boosts, ["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK", "BBNI.JK"], 0.030)
    if commodity_spillover > 0.52:
        _add_boosts(boosts, IHSG_BUCKETS.get("Coal/Energy", []) + IHSG_BUCKETS.get("Metals", []), 0.018)
    if usd_pressure > 0.58 or ctx["risk_off_penalty"] > 0.55:
        _add_boosts(boosts, ["BBCA.JK", "TLKM.JK", "ICBP.JK", "INDF.JK", "KLBF.JK", "AMRT.JK"], 0.016)
    ctx["theme_boosts"] = boosts
    return ctx


def fx_ranking_context(shared_core: dict, features: dict | None = None) -> dict:
    features = features or {}
    ribbon = shared_core.get("status_ribbon", {}) or {}
    structural = str(ribbon.get("structural_quad", "Q3"))
    monthly = str(ribbon.get("monthly_quad", structural))
    regime_map = {"Q1": 0.52, "Q2": 0.60, "Q3": 0.56, "Q4": 0.46}
    regime = 0.6 * regime_map.get(structural, 0.5) + 0.4 * regime_map.get(monthly, 0.5)
    breadth = clamp01(features.get("pair_breadth", 0.5))
    execution = clamp01(features.get("execution_state", {}).get("score", 0.5))
    ctx = _status_terms(shared_core, regime, breadth, execution)
    ctx["theme_boosts"] = {}
    return ctx


def commodity_ranking_context(shared_core: dict, features: dict | None = None) -> dict:
    features = features or {}
    ribbon = shared_core.get("status_ribbon", {}) or {}
    structural = str(ribbon.get("structural_quad", "Q3"))
    monthly = str(ribbon.get("monthly_quad", structural))
    regime_map = {"Q1": 0.58, "Q2": 0.70, "Q3": 0.56, "Q4": 0.44}
    regime = 0.6 * regime_map.get(structural, 0.5) + 0.4 * regime_map.get(monthly, 0.5)
    breadth = clamp01(features.get("physical_balance", 0.5))
    execution = clamp01(features.get("execution_state", {}).get("score", 0.5))
    ctx = _status_terms(shared_core, regime, breadth, execution)
    boosts: dict[str, float] = {}
    if clamp01(shared_core.get("petrodollar", {}).get("score", 0.0)) > 0.55 or str(shared_core.get("news_state", {}).get("state", "quiet")) == "war_oil":
        _add_boosts(boosts, COMMODITY_BUCKETS.get("Energy", []), 0.024)
    if ctx["risk_off_penalty"] > 0.52 or clamp01(features.get("usd_rates_pressure", 0.5)) < 0.45:
        _add_boosts(boosts, COMMODITY_BUCKETS.get("Precious", []), 0.020)
    ctx["theme_boosts"] = boosts
    return ctx


def crypto_ranking_context(shared_core: dict, features: dict | None = None) -> dict:
    features = features or {}
    ribbon = shared_core.get("status_ribbon", {}) or {}
    structural = str(ribbon.get("structural_quad", "Q3"))
    monthly = str(ribbon.get("monthly_quad", structural))
    regime_map = {"Q1": 0.64, "Q2": 0.76, "Q3": 0.40, "Q4": 0.24}
    regime = 0.6 * regime_map.get(structural, 0.5) + 0.4 * regime_map.get(monthly, 0.5)
    breadth = clamp01(features.get("breadth_score", 0.5))
    execution = clamp01(features.get("execution_state", {}).get("score", 0.5))
    ctx = _status_terms(shared_core, regime, breadth, execution)
    boosts: dict[str, float] = {}
    fragility = clamp01(features.get("liquidity_fragility", 0.5))
    flow = clamp01(features.get("flow", 0.5))
    if flow > 0.55 and fragility < 0.50 and ctx["risk_off_penalty"] < 0.55:
        _add_boosts(boosts, CRYPTO_BUCKETS.get("AI/Data", []) + CRYPTO_BUCKETS.get("RWA", []) + CRYPTO_BUCKETS.get("Infra", []), 0.022)
        _add_boosts(boosts, CRYPTO_BUCKETS.get("High Beta", []), 0.015)
    if fragility > 0.58 or ctx["risk_off_penalty"] > 0.58:
        _add_boosts(boosts, CRYPTO_BUCKETS.get("Majors", []) + ["LINK-USD", "INJ-USD"], 0.020)
    ctx["theme_boosts"] = boosts
    return ctx
