from __future__ import annotations
from typing import Dict

import numpy as np
import pandas as pd


def _safe_series(s) -> pd.Series:
    if s is None:
        return pd.Series(dtype=float)
    if isinstance(s, pd.Series):
        return pd.to_numeric(s, errors="coerce").dropna()
    return pd.Series(dtype=float)


def last(s) -> float:
    s = _safe_series(s)
    return float(s.iloc[-1]) if not s.empty else float("nan")


def ret_n(s, n: int) -> float:
    s = _safe_series(s)
    if len(s) < n + 1:
        return float("nan")
    base = float(s.iloc[-(n + 1)])
    if not np.isfinite(base) or base == 0:
        return float("nan")
    return float(s.iloc[-1] / base - 1.0)


def delta_n(s, n: int) -> float:
    s = _safe_series(s)
    if len(s) < n + 1:
        return float("nan")
    return float(s.iloc[-1] - s.iloc[-(n + 1)])


def _scaled(x: float, scale: float) -> float:
    if not np.isfinite(x):
        return float("nan")
    return float(np.tanh(x / scale))


def _fallback_price_proxy(prices: Dict[str, pd.Series]) -> dict:
    spy_3m = ret_n(prices.get("SPY"), 63)
    xli_3m = ret_n(prices.get("XLI"), 63)
    xly_3m = ret_n(prices.get("XLY"), 63)
    iwm_3m = ret_n(prices.get("IWM"), 63)
    xhb_3m = ret_n(prices.get("XHB"), 63)
    uup_3m = ret_n(prices.get("UUP"), 63)
    oil_3m = ret_n(prices.get("CL=F"), 63)
    gold_3m = ret_n(prices.get("GC=F"), 63)
    breakeven_proxy = 2.2 + 1.2 * np.nan_to_num(oil_3m, nan=0.0) + 0.4 * np.nan_to_num(gold_3m, nan=0.0) - 0.2 * np.nan_to_num(uup_3m, nan=0.0)
    return {
        "indpro_yoy": float(np.nan_to_num(0.55 * xli_3m + 0.45 * spy_3m, nan=0.0)),
        "retail_yoy": float(np.nan_to_num(0.60 * xly_3m + 0.40 * spy_3m, nan=0.0)),
        "payrolls_yoy": float(np.nan_to_num(0.50 * iwm_3m + 0.50 * spy_3m, nan=0.0)),
        "unrate_3m_delta": float(np.nan_to_num(-0.10 * iwm_3m, nan=0.0)),
        "claims_13w_delta": float(np.nan_to_num(-10.0 * iwm_3m, nan=0.0)),
        "ism_last": float(np.nan_to_num(50.0 + 20.0 * xli_3m, nan=50.0)),
        "housing_yoy": float(np.nan_to_num(0.70 * xhb_3m + 0.30 * iwm_3m, nan=0.0)),
        "cpi_yoy": float(np.nan_to_num(0.025 + 0.35 * oil_3m + 0.05 * gold_3m, nan=0.025)),
        "core_cpi_yoy": float(np.nan_to_num(0.023 + 0.15 * oil_3m - 0.05 * uup_3m, nan=0.023)),
        "breakeven_last": float(np.nan_to_num(breakeven_proxy, nan=2.2)),
    }


def build_macro_features(fred: Dict[str, pd.Series], prices: Dict[str, pd.Series], loader_meta: Dict[str, dict] | None = None) -> Dict[str, float]:
    loader_meta = loader_meta or {}
    fred_meta = loader_meta.get("fred", {}) if isinstance(loader_meta, dict) else {}
    price_meta = loader_meta.get("prices", {}) if isinstance(loader_meta, dict) else {}
    features = {
        "indpro_yoy": ret_n(fred.get("INDPRO"), 12),
        "retail_yoy": ret_n(fred.get("RSAFS"), 12),
        "payrolls_yoy": ret_n(fred.get("PAYEMS"), 12),
        "unrate_3m_delta": delta_n(fred.get("UNRATE"), 3),
        "claims_13w_delta": delta_n(fred.get("ICSA"), 13),
        "ism_last": last(fred.get("ISMNO")),
        "housing_yoy": ret_n(fred.get("HOUST"), 12),
        "cpi_yoy": ret_n(fred.get("CPI"), 12),
        "core_cpi_yoy": ret_n(fred.get("CORECPI"), 12),
        "breakeven_last": last(fred.get("T5YIE")),
        "breakeven_1m_delta": delta_n(fred.get("T5YIE"), 1),
        "real_10y_last": last(fred.get("DFII10")),
        "policy_rate_level": last(fred.get("FEDFUNDS")),
        "policy_rate_3m_delta": delta_n(fred.get("FEDFUNDS"), 3),
        "oil_3m": ret_n(prices.get("CL=F"), 63),
        "gold_3m": ret_n(prices.get("GC=F"), 63),
        "dxy_3m": ret_n(prices.get("UUP"), 63),
        "oil_1m": ret_n(prices.get("CL=F"), 21),
        "gold_1m": ret_n(prices.get("GC=F"), 21),
        "dxy_1m": ret_n(prices.get("UUP"), 21),
        "spy_1m": ret_n(prices.get("SPY"), 21),
        "xli_1m": ret_n(prices.get("XLI"), 21),
        "xly_1m": ret_n(prices.get("XLY"), 21),
        "iwm_1m": ret_n(prices.get("IWM"), 21),
        "xhb_1m": ret_n(prices.get("XHB"), 21),
        "tlt_1m": ret_n(prices.get("TLT"), 21),
    }

    proxy = _fallback_price_proxy(prices)
    raw_macro_keys = [
        "indpro_yoy", "retail_yoy", "payrolls_yoy", "unrate_3m_delta", "claims_13w_delta",
        "ism_last", "housing_yoy", "cpi_yoy", "core_cpi_yoy", "breakeven_last",
    ]
    proxy_used = 0
    proxy_used_keys = []
    for k in raw_macro_keys:
        if not np.isfinite(features[k]):
            features[k] = proxy[k]
            proxy_used += 1
            proxy_used_keys.append(k)

    growth_inputs = [
        _scaled(features["indpro_yoy"] - 0.02, 0.05),
        _scaled(features["retail_yoy"] - 0.03, 0.06),
        _scaled(features["payrolls_yoy"] - 0.015, 0.03),
        _scaled(features["housing_yoy"], 0.10),
        _scaled((features["ism_last"] - 50.0) / 100.0, 0.04),
        _scaled(-(features["unrate_3m_delta"]), 0.12),
        _scaled(-(features["claims_13w_delta"] / 40.0), 0.60),
    ]
    growth_mom_inputs = [
        _scaled(features["housing_yoy"], 0.08),
        _scaled(features["indpro_yoy"], 0.05),
        _scaled(-(features["unrate_3m_delta"]), 0.10),
        _scaled(-(features["claims_13w_delta"] / 50.0), 0.50),
    ]
    inflation_inputs = [
        _scaled(features["cpi_yoy"] - 0.025, 0.02),
        _scaled(features["core_cpi_yoy"] - 0.025, 0.015),
        _scaled((features["breakeven_last"] - 2.2) / 2.0, 0.30),
        _scaled(features["oil_3m"], 0.25),
        _scaled(features["gold_3m"], 0.18),
    ]
    inflation_mom_inputs = [
        _scaled(features["oil_3m"], 0.22),
        _scaled(features["gold_3m"], 0.18),
        _scaled((features["breakeven_last"] - 2.2) / 2.0, 0.24),
        _scaled(features["dxy_3m"], 0.14),
    ]

    growth_level = float(np.nanmean(growth_inputs))
    growth_momentum = float(np.nanmean(growth_mom_inputs))
    inflation_level = float(np.nanmean(inflation_inputs))
    inflation_momentum = float(np.nanmean(inflation_mom_inputs))

    slowdown_flags = sum([
        1 if np.isfinite(features["unrate_3m_delta"]) and features["unrate_3m_delta"] > 0.05 else 0,
        1 if np.isfinite(features["claims_13w_delta"]) and features["claims_13w_delta"] > 0 else 0,
        1 if np.isfinite(features["ism_last"]) and features["ism_last"] < 50 else 0,
        1 if np.isfinite(features["housing_yoy"]) and features["housing_yoy"] < 0 else 0,
    ]) / 4.0

    data_points = [*growth_inputs, *inflation_inputs]
    coverage = float(np.mean([1.0 if np.isfinite(x) else 0.0 for x in data_points])) if data_points else 0.75
    inflation_shock = float(np.nanmean([
        _scaled(features["oil_3m"], 0.22),
        _scaled((features["breakeven_last"] - 2.2) / 2.0, 0.24),
        _scaled(features["dxy_3m"], 0.14),
    ]))

    liquidity_proxy = float(np.nanmean([
        _scaled(-features.get("dxy_3m", float("nan")), 0.12),
        _scaled(features.get("tlt_1m", float("nan")), 0.08),
    ]))
    policy_score = _scaled(-features.get("policy_rate_3m_delta", float("nan")), 0.50)
    liquidity_score = _scaled(liquidity_proxy, 0.50)
    raw_macro_real_share = 1.0 - (proxy_used / max(len(raw_macro_keys), 1))
    fred_real_share = float(fred_meta.get("real_share", raw_macro_real_share)) if isinstance(fred_meta, dict) else raw_macro_real_share
    price_real_share = float(price_meta.get("real_share", 0.0)) if isinstance(price_meta, dict) else 0.0
    macro_proxy_share = float(max(0.0, min(1.0, 1.0 - raw_macro_real_share)))
    macro_real_share = float(max(0.0, min(1.0, raw_macro_real_share)))
    monthly_real_share = float(max(0.0, min(1.0, np.mean([
        1.0 if np.isfinite(features.get("oil_1m", float("nan"))) else 0.0,
        1.0 if np.isfinite(features.get("gold_1m", float("nan"))) else 0.0,
        1.0 if np.isfinite(features.get("dxy_1m", float("nan"))) else 0.0,
        1.0 if np.isfinite(features.get("spy_1m", float("nan"))) else 0.0,
        1.0 if np.isfinite(features.get("xli_1m", float("nan"))) else 0.0,
        1.0 if np.isfinite(features.get("xly_1m", float("nan"))) else 0.0,
        1.0 if np.isfinite(features.get("iwm_1m", float("nan"))) else 0.0,
    ]))))
    structural_real_share = float(max(0.0, min(1.0, 0.70 * fred_real_share + 0.30 * macro_real_share)))
    monthly_data_coverage = float(max(0.0, min(1.0, 0.60 * monthly_real_share + 0.25 * price_real_share + 0.15 * structural_real_share)))
    data_coverage = float(max(0.0, min(1.0, 0.70 * structural_real_share + 0.30 * coverage)))
    macro_confidence_penalty = 0.35 * macro_proxy_share + 0.15 * max(0.0, 1.0 - fred_real_share)

    # Dual-horizon scaffolding.
    headline_core_gap = float(features["cpi_yoy"] - features["core_cpi_yoy"]) if np.isfinite(features.get("cpi_yoy")) and np.isfinite(features.get("core_cpi_yoy")) else float("nan")
    monthly_growth_inputs = [
        _scaled(features["spy_1m"], 0.05),
        _scaled(features["xli_1m"], 0.05),
        _scaled(features["xly_1m"], 0.05),
        _scaled(features["iwm_1m"], 0.07),
        _scaled(features["xhb_1m"], 0.08),
        _scaled(-features["dxy_1m"], 0.06),
    ]
    monthly_inflation_inputs = [
        _scaled(headline_core_gap, 0.004),
        _scaled(features["oil_1m"], 0.06),
        _scaled(features["gold_1m"], 0.05),
        _scaled(features["breakeven_1m_delta"], 0.08),
        _scaled(-features["dxy_1m"], 0.05),
    ]

    monthly_growth_signal = float(np.nanmean(monthly_growth_inputs)) if monthly_growth_inputs else 0.0
    monthly_inflation_signal = float(np.nanmean(monthly_inflation_inputs)) if monthly_inflation_inputs else 0.0

    growth_structural_level = float(np.nan_to_num(growth_level, nan=0.0))
    growth_structural_momentum = float(np.nan_to_num(growth_momentum, nan=0.0))
    inflation_structural_level = float(np.nan_to_num(inflation_level, nan=0.0))
    inflation_structural_momentum = float(np.nan_to_num(inflation_momentum, nan=0.0))

    growth_monthly_level = float(np.nan_to_num(0.65 * growth_level + 0.35 * growth_momentum, nan=0.0))
    growth_monthly_momentum = float(np.nan_to_num(0.45 * growth_momentum + 0.55 * monthly_growth_signal, nan=0.0))
    inflation_monthly_level = float(np.nan_to_num(0.55 * inflation_level + 0.25 * inflation_momentum + 0.20 * _scaled(headline_core_gap, 0.004), nan=0.0))
    inflation_monthly_momentum = float(np.nan_to_num(0.45 * inflation_momentum + 0.55 * monthly_inflation_signal, nan=0.0))

    monthly_policy_score = float(np.nan_to_num(0.60 * policy_score + 0.40 * _scaled(-features.get("policy_rate_3m_delta", float("nan")), 0.25), nan=0.0))
    monthly_liquidity_score = float(np.nan_to_num(0.50 * liquidity_score + 0.50 * _scaled(liquidity_proxy, 0.35), nan=0.0))
    monthly_inflation_shock = float(np.nan_to_num(np.nanmean([
        max(0.0, _scaled(headline_core_gap, 0.004)) if np.isfinite(_scaled(headline_core_gap, 0.004)) else np.nan,
        max(0.0, _scaled(features["oil_1m"], 0.06)) if np.isfinite(_scaled(features["oil_1m"], 0.06)) else np.nan,
        max(0.0, _scaled(features["breakeven_1m_delta"], 0.08)) if np.isfinite(_scaled(features["breakeven_1m_delta"], 0.08)) else np.nan,
    ]), nan=0.0))

    features.update({
        "growth_level": float(np.nan_to_num(growth_level, nan=0.0)),
        "growth_momentum": float(np.nan_to_num(growth_momentum, nan=0.0)),
        "inflation_level": float(np.nan_to_num(inflation_level, nan=0.0)),
        "inflation_momentum": float(np.nan_to_num(inflation_momentum, nan=0.0)),
        "slowdown_flags": slowdown_flags,
        "inflation_shock": float(np.nan_to_num(inflation_shock, nan=0.0)),
        "data_coverage_raw": coverage,
        "data_coverage": data_coverage,
        "proxy_used_count": int(proxy_used),
        "proxy_used_keys": proxy_used_keys,
        "macro_proxy_share": float(macro_proxy_share),
        "macro_real_share": float(macro_real_share),
        "fred_real_share": float(max(0.0, min(1.0, fred_real_share))),
        "price_real_share": float(max(0.0, min(1.0, price_real_share))),
        "structural_real_share": float(structural_real_share),
        "monthly_real_share": float(monthly_real_share),
        "monthly_data_coverage": float(monthly_data_coverage),
        "macro_confidence_penalty": float(macro_confidence_penalty),
        "policy_score": float(np.nan_to_num(policy_score, nan=0.0)),
        "liquidity_proxy": float(np.nan_to_num(liquidity_proxy, nan=0.0)),
        "liquidity_score": float(np.nan_to_num(liquidity_score, nan=0.0)),
        "macro_complete": int(sum(1 for k in raw_macro_keys if np.isfinite(features.get(k, float("nan"))))),
        "growth_structural_level": growth_structural_level,
        "growth_structural_momentum": growth_structural_momentum,
        "inflation_structural_level": inflation_structural_level,
        "inflation_structural_momentum": inflation_structural_momentum,
        "growth_monthly_level": growth_monthly_level,
        "growth_monthly_momentum": growth_monthly_momentum,
        "inflation_monthly_level": inflation_monthly_level,
        "inflation_monthly_momentum": inflation_monthly_momentum,
        "monthly_policy_score": monthly_policy_score,
        "monthly_liquidity_score": monthly_liquidity_score,
        "monthly_inflation_shock": monthly_inflation_shock,
        "headline_core_gap": float(np.nan_to_num(headline_core_gap, nan=0.0)),
    })
    return features
