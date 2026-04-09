from __future__ import annotations
from typing import Dict, List, Union

from utils.math_utils import clamp01


def build_scenario_features(macro: Dict[str, float], market: Dict[str, float], plumbing: Dict[str, float]) -> Dict[str, Union[float, List[str]]]:
    flags: list[str] = []

    oil_3m = float(macro.get("oil_3m", 0.0) or 0.0)
    infl = float(macro.get("inflation_momentum", 0.0) or 0.0)
    growth = float(macro.get("growth_momentum", 0.0) or 0.0)
    dxy_1m = float(market.get("dxy_1m", 0.0) or 0.0)
    eem_rel = float(market.get("eem_rel_1m", 0.0) or 0.0)
    ihsg_rel = float(market.get("ihsg_rel_1m", 0.0) or 0.0)
    iwm_rel = float(market.get("iwm_rel_1m", 0.0) or 0.0)
    tlt_1m = float(market.get("tlt_1m", 0.0) or 0.0)
    vix_1m = float(market.get("vix_1m", 0.0) or 0.0)
    xle_rel = float(market.get("xle_rel_1m", 0.0) or 0.0)
    xlp_rel = float(market.get("xlp_rel_1m", 0.0) or 0.0)
    xlv_rel = float(market.get("xlv_rel_1m", 0.0) or 0.0)
    gold_3m = float(macro.get("gold_3m", 0.0) or 0.0)
    dollar_pressure = float(plumbing.get("dollar_pressure", 0.5) or 0.5)
    yields_pressure = float(plumbing.get("yield_pressure", 0.5) or 0.5)

    oil_shock = 1.0 if oil_3m > 0.10 else 0.0
    usd_pressure = 1.0 if dollar_pressure > 0.60 else 0.0
    small_cap_failure = 1.0 if iwm_rel < -0.03 else 0.0
    vol_rising = 1.0 if vix_1m > 0.10 else 0.0

    petrodollar_shock = clamp01(
        0.38 * clamp01(0.5 + oil_3m / 0.12)
        + 0.24 * clamp01(0.5 + dxy_1m / 0.04)
        + 0.18 * clamp01(0.5 + max(0.0, -eem_rel) / 0.05)
        + 0.20 * clamp01(0.5 + yields_pressure)
    )
    em_importer_pain = clamp01(
        0.35 * petrodollar_shock
        + 0.25 * clamp01(0.5 + max(0.0, -ihsg_rel) / 0.05)
        + 0.20 * clamp01(0.5 + max(0.0, -eem_rel) / 0.05)
        + 0.20 * clamp01(0.5 + dxy_1m / 0.04)
    )
    petro_exporter_benefit = clamp01(
        0.40 * clamp01(0.5 + oil_3m / 0.12)
        + 0.25 * clamp01(0.5 + xle_rel / 0.05)
        + 0.20 * clamp01(0.5 + ihsg_rel / 0.05)
        + 0.15 * clamp01(0.5 + gold_3m / 0.10)
    )
    shipping_chokepoint = clamp01(
        0.45 * clamp01(0.5 + oil_3m / 0.12)
        + 0.25 * clamp01(0.5 + vix_1m / 0.12)
        + 0.30 * clamp01(0.5 + dxy_1m / 0.04)
    )
    carry_unwind = clamp01(
        0.35 * clamp01(0.5 + dxy_1m / 0.04)
        + 0.35 * clamp01(0.5 + max(0.0, -tlt_1m) / 0.05)
        + 0.30 * clamp01(0.5 + vix_1m / 0.12)
    )
    inflation_reaccel = clamp01(
        0.40 * clamp01(0.5 + infl / 0.15)
        + 0.30 * clamp01(0.5 + oil_3m / 0.12)
        + 0.15 * clamp01(0.5 + gold_3m / 0.10)
        + 0.15 * clamp01(0.5 + dxy_1m / 0.04)
    )
    growth_scare = clamp01(
        0.45 * clamp01(0.5 + max(0.0, -growth) / 0.15)
        + 0.30 * clamp01(0.5 + max(0.0, -iwm_rel) / 0.05)
        + 0.25 * clamp01(0.5 + max(0.0, -tlt_1m) / 0.05)
    )
    china_false_dawn = clamp01(
        0.35 * clamp01(0.5 + oil_3m / 0.10)
        + 0.25 * clamp01(0.5 + infl / 0.12)
        + 0.20 * clamp01(0.5 + max(0.0, -eem_rel) / 0.05)
        + 0.20 * clamp01(0.5 + max(0.0, -ihsg_rel) / 0.05)
    )
    dollar_liquidity_squeeze = clamp01(
        0.40 * clamp01(0.5 + dxy_1m / 0.04)
        + 0.25 * yields_pressure
        + 0.20 * vol_rising
        + 0.15 * clamp01(0.5 + max(0.0, -eem_rel) / 0.05)
    )
    defensive_breadth_failure = clamp01(
        0.35 * clamp01(0.5 + max(0.0, -iwm_rel) / 0.05)
        + 0.20 * clamp01(0.5 + max(0.0, -eem_rel) / 0.05)
        + 0.20 * clamp01(0.5 + xlp_rel / 0.04)
        + 0.25 * clamp01(0.5 + xlv_rel / 0.04)
    )
    broadening_reflation = clamp01(
        0.30 * clamp01(0.5 + max(0.0, -dxy_1m) / 0.04)
        + 0.25 * clamp01(0.5 + eem_rel / 0.05)
        + 0.25 * clamp01(0.5 + ihsg_rel / 0.05)
        + 0.20 * clamp01(0.5 + max(0.0, -vix_1m) / 0.08)
    )
    historical_repeat_score = clamp01(
        0.25 * inflation_reaccel
        + 0.20 * growth_scare
        + 0.15 * carry_unwind
        + 0.15 * petrodollar_shock
        + 0.10 * shipping_chokepoint
        + 0.15 * defensive_breadth_failure
    )

    if oil_shock:
        flags.append("oil_shock")
    if usd_pressure:
        flags.append("usd_pressure")
    if small_cap_failure:
        flags.append("small_cap_failure")
    if vol_rising:
        flags.append("vol_rising")
    if petrodollar_shock >= 0.62:
        flags.append("petrodollar_shock")
    if em_importer_pain >= 0.60:
        flags.append("em_importer_pain")
    if petro_exporter_benefit >= 0.60:
        flags.append("petro_exporter_benefit")
    if shipping_chokepoint >= 0.60:
        flags.append("shipping_chokepoint")
    if carry_unwind >= 0.60:
        flags.append("carry_unwind")
    if inflation_reaccel >= 0.60 and growth_scare >= 0.55:
        flags.append("stagflation_repeat")
    if china_false_dawn >= 0.58:
        flags.append("china_false_dawn")
    if dollar_liquidity_squeeze >= 0.60:
        flags.append("dollar_liquidity_squeeze")
    if broadening_reflation >= 0.58:
        flags.append("broadening_reflation")

    return {
        "oil_shock": oil_shock,
        "usd_pressure": usd_pressure,
        "small_cap_failure": small_cap_failure,
        "vol_rising": vol_rising,
        "petrodollar_shock": petrodollar_shock,
        "em_importer_pain": em_importer_pain,
        "petro_exporter_benefit": petro_exporter_benefit,
        "shipping_chokepoint": shipping_chokepoint,
        "carry_unwind": carry_unwind,
        "inflation_reaccel": inflation_reaccel,
        "growth_scare": growth_scare,
        "china_false_dawn": china_false_dawn,
        "dollar_liquidity_squeeze": dollar_liquidity_squeeze,
        "defensive_breadth_failure": defensive_breadth_failure,
        "broadening_reflation": broadening_reflation,
        "historical_repeat_score": historical_repeat_score,
        "flags": flags,
    }
