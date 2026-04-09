from __future__ import annotations

from config.ihsg_structural_registry import IHSG_CLEAN_FLOAT_BENEFICIARIES, IHSG_STRUCTURAL_REGISTRY
from utils.math_utils import clamp01


DEFAULT_STRUCTURAL_STATE = {
    "symbol_adjustments": {},
    "symbol_flags": {},
    "symbol_meta": {},
    "beneficiary_boosts": {},
    "clean_float_rotation_score": 0.0,
    "registry_coverage": 0,
}


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _fragility_components(entry: dict[str, object]) -> tuple[float, float, float, float, float, float, float]:
    hsc = clamp01(_safe_float(entry.get("hsc", 0.0)))
    free_float = clamp01(_safe_float(entry.get("free_float", 1.0), 1.0))
    msci_fragility = clamp01(_safe_float(entry.get("msci_fragility", 0.0)))
    ownership_opacity = clamp01(_safe_float(entry.get("ownership_opacity", 0.0)))
    data_confidence = clamp01(_safe_float(entry.get("data_confidence", 0.75), 0.75))
    hsc_norm = clamp01((hsc - 0.85) / 0.15)
    free_float_deficit = clamp01((0.15 - free_float) / 0.15)
    fragility_raw = (
        0.35 * hsc_norm
        + 0.30 * free_float_deficit
        + 0.20 * msci_fragility
        + 0.15 * ownership_opacity
    )
    fragility = clamp01(fragility_raw * data_confidence)
    return hsc_norm, free_float_deficit, msci_fragility, ownership_opacity, data_confidence, fragility_raw, fragility


def build_ihsg_structural_state(shared_core: dict | None = None, base_features: dict | None = None) -> dict:
    shared_core = shared_core or {}
    base_features = base_features or {}
    risk_summary = shared_core.get("risk_summary", {}) or {}
    em_rotation = shared_core.get("em_rotation", {}) or {}

    foreign_flow = clamp01(_safe_float(base_features.get("foreign_flow", 0.5), 0.5))
    breadth_liquidity = clamp01(_safe_float(base_features.get("breadth_liquidity", 0.5), 0.5))
    global_risk = clamp01(_safe_float(base_features.get("global_risk", 0.5), 0.5))
    usd_idr_pressure = clamp01(_safe_float(base_features.get("usd_idr_pressure", 0.5), 0.5))
    em_score = clamp01(_safe_float(em_rotation.get("resolved_score", em_rotation.get("score", 0.4)), 0.4))
    risk_off_penalty = clamp01(_safe_float(risk_summary.get("risk_off_score", 0.0)) / 4.0)

    clean_float_rotation_score = clamp01(
        0.35 * foreign_flow
        + 0.25 * breadth_liquidity
        + 0.20 * global_risk
        + 0.15 * em_score
        + 0.05 * (1.0 - usd_idr_pressure)
    )

    symbol_adjustments: dict[str, float] = {}
    symbol_flags: dict[str, str] = {}
    symbol_meta: dict[str, dict[str, float | str | bool]] = {}

    for symbol, entry in IHSG_STRUCTURAL_REGISTRY.items():
        hsc_norm, free_float_deficit, msci_fragility, ownership_opacity, data_confidence, fragility_raw, fragility = _fragility_components(entry)
        conflict_penalty = 0.85 if bool(entry.get("source_conflict", False)) else 1.0
        structural_adjustment = -0.07 * fragility * conflict_penalty
        flag = str(entry.get("manual_flag", "Structural fragility"))
        symbol_adjustments[symbol] = float(structural_adjustment)
        symbol_flags[symbol] = flag
        symbol_meta[symbol] = {
            "hsc_norm": round(hsc_norm, 4),
            "free_float_deficit": round(free_float_deficit, 4),
            "msci_fragility": round(msci_fragility, 4),
            "ownership_opacity": round(ownership_opacity, 4),
            "data_confidence": round(data_confidence, 4),
            "structural_fragility_raw": round(fragility_raw, 4),
            "structural_fragility": round(fragility, 4),
            "structural_adjustment": round(structural_adjustment, 4),
            "source_conflict": bool(entry.get("source_conflict", False)),
            "as_of": str(entry.get("as_of", "")),
        }

    beneficiary_boosts: dict[str, float] = {}
    if clean_float_rotation_score >= 0.54 and foreign_flow >= 0.48 and breadth_liquidity >= 0.48 and risk_off_penalty < 0.60:
        boost = 0.012 + 0.013 * clamp01((clean_float_rotation_score - 0.54) / 0.36)
        for symbol in IHSG_CLEAN_FLOAT_BENEFICIARIES:
            beneficiary_boosts[symbol] = round(float(boost), 4)

    return {
        "symbol_adjustments": symbol_adjustments,
        "symbol_flags": symbol_flags,
        "symbol_meta": symbol_meta,
        "beneficiary_boosts": beneficiary_boosts,
        "clean_float_rotation_score": round(clean_float_rotation_score, 4),
        "registry_coverage": len(IHSG_STRUCTURAL_REGISTRY),
    }
