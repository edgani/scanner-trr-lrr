from __future__ import annotations
from typing import Dict
import numpy as np
import pandas as pd


SECTOR_ETFS = ["XLE", "XLF", "XLI", "XLB", "XLK", "XLV", "XLY", "XLP", "XLU", "XLRE", "XLC"]


def _safe_series(s):
    if s is None:
        return pd.Series(dtype=float)
    if isinstance(s, pd.Series):
        return pd.to_numeric(s, errors="coerce").dropna()
    return pd.Series(dtype=float)


def ret_n(s, n: int) -> float:
    s = _safe_series(s)
    if len(s) < n + 1:
        return float("nan")
    base = float(s.iloc[-(n + 1)])
    if not np.isfinite(base) or base == 0:
        return float("nan")
    return float(s.iloc[-1] / base - 1.0)


def trend_score(s) -> float:
    s = _safe_series(s)
    if len(s) < 50:
        return 0.5
    px = float(s.iloc[-1])
    ma20 = s.rolling(20).mean().iloc[-1]
    ma50 = s.rolling(50).mean().iloc[-1]
    score = 0.0
    score += 0.5 if px > ma20 else 0.0
    score += 0.5 if px > ma50 else 0.0
    return float(score)


def _score_positive(x: float, good: float = 0.0, full: float = 0.08) -> float:
    if not np.isfinite(x):
        return 0.5
    if x <= good:
        return 0.0
    if x >= full:
        return 1.0
    return float((x - good) / max(full - good, 1e-9))


def _score_negative(x: float, good: float = 0.0, full: float = -0.05) -> float:
    if not np.isfinite(x):
        return 0.5
    if x >= good:
        return 0.0
    if x <= full:
        return 1.0
    return float((good - x) / max(good - full, 1e-9))



def _breadth_trend_state(breadth_health: float, narrow_leadership: float, sector_support_ratio: float) -> str:
    """
    UI-facing breadth trend proxy:
    - broadening: broad participation, lower concentration risk
    - fragile: mixed participation / concentration not extreme
    - deteriorating: weak participation or concentration dominates
    """
    if breadth_health >= 0.62 and narrow_leadership <= 0.42 and sector_support_ratio >= 0.55:
        return "broadening"
    if breadth_health <= 0.42 or narrow_leadership >= 0.62 or sector_support_ratio <= 0.35:
        return "deteriorating"
    return "fragile"

def build_market_features(prices: Dict[str, pd.Series]) -> Dict[str, float]:
    spy = prices.get("SPY")
    qqq = prices.get("QQQ")
    iwm = prices.get("IWM")
    rsp = prices.get("RSP")
    hyg = prices.get("HYG")
    tlt = prices.get("TLT")
    uup = prices.get("UUP")
    vix = prices.get("^VIX")
    eem = prices.get("EEM")
    ihsg = prices.get("^JKSE")
    xau = prices.get("GC=F")
    wti = prices.get("CL=F")

    spy_1m = ret_n(spy, 21)
    spy_3m = ret_n(spy, 63)
    qqq_1m = ret_n(qqq, 21)
    qqq_3m = ret_n(qqq, 63)
    iwm_rel_1m = ret_n(iwm, 21) - spy_1m
    rsp_rel_1m = ret_n(rsp, 21) - spy_1m
    rsp_rel_3m = ret_n(rsp, 63) - spy_3m
    eem_rel_1m = ret_n(eem, 21) - spy_1m
    eem_rel_3m = ret_n(eem, 63) - spy_3m
    ihsg_rel_1m = ret_n(ihsg, 21) - spy_1m
    dxy_1m = ret_n(uup, 21)
    tlt_1m = ret_n(tlt, 21)

    sector_1m = {sym: ret_n(prices.get(sym), 21) for sym in SECTOR_ETFS}
    sector_3m = {sym: ret_n(prices.get(sym), 63) for sym in SECTOR_ETFS}
    sector_support_1m = int(sum(1 for v in sector_1m.values() if np.isfinite(v) and v > 0))
    sector_support_3m = int(sum(1 for v in sector_3m.values() if np.isfinite(v) and v > 0))
    sector_support_ratio = sector_support_1m / max(len(SECTOR_ETFS), 1)

    eqw_health = 0.5 * _score_positive(rsp_rel_1m, 0.0, 0.03) + 0.5 * _score_positive(rsp_rel_3m, 0.0, 0.05)
    smallcap_health = _score_positive(iwm_rel_1m, 0.0, 0.05)
    breadth_health = float(np.nanmean([sector_support_ratio, eqw_health, smallcap_health]))

    narrow_leadership = float(np.nanmean([
        _score_positive(qqq_1m - spy_1m, 0.0, 0.04),
        _score_negative(rsp_rel_1m, 0.0, -0.03),
        _score_negative(iwm_rel_1m, 0.0, -0.04),
        1.0 - sector_support_ratio,
    ]))

    escape_scores = {
        "XAUUSD": float(np.nanmean([_score_positive(ret_n(xau, 21), 0.0, 0.05), _score_negative(dxy_1m, 0.0, -0.03)])),
        "TLT": float(np.nanmean([_score_positive(tlt_1m, 0.0, 0.04), _score_negative(ret_n(vix, 21), 0.0, -0.08)])),
        "EEM": float(np.nanmean([_score_positive(eem_rel_1m, 0.0, 0.05), _score_positive(eem_rel_3m, 0.0, 0.08)])),
        "IHSG": float(np.nanmean([_score_positive(ihsg_rel_1m, 0.0, 0.04), _score_negative(dxy_1m, 0.0, -0.03)])),
        "WTI": float(np.nanmean([_score_positive(ret_n(wti, 21), 0.0, 0.08), _score_positive(ret_n(wti, 63), 0.0, 0.10)])),
        "USD": float(np.nanmean([_score_positive(dxy_1m, 0.0, 0.03), _score_negative(ret_n(hyg, 21), 0.0, -0.03)])),
    }
    escape_route = max(escape_scores.items(), key=lambda kv: kv[1])[0] if escape_scores else "USD"

    rotation_components = [
        _score_positive(eem_rel_1m, 0.0, 0.05),
        _score_positive(eem_rel_3m, 0.0, 0.08),
        _score_positive(ihsg_rel_1m, 0.0, 0.05),
        _score_negative(dxy_1m, 0.0, -0.03),
        _score_positive(rsp_rel_1m, 0.0, 0.03),
        _score_positive(tlt_1m, 0.0, 0.04),
    ]
    em_rotation_score = float(np.nanmean(rotation_components))

    breadth_trend_state = _breadth_trend_state(float(breadth_health), float(narrow_leadership), float(sector_support_ratio))

    features = {
        "spy_1m": spy_1m,
        "spy_3m": spy_3m,
        "qqq_1m": qqq_1m,
        "qqq_3m": qqq_3m,
        "iwm_rel_1m": iwm_rel_1m,
        "rsp_rel_1m": rsp_rel_1m,
        "rsp_rel_3m": rsp_rel_3m,
        "hyg_1m": ret_n(hyg, 21),
        "tlt_1m": tlt_1m,
        "dxy_1m": dxy_1m,
        "vix_1m": ret_n(vix, 21),
        "spy_trend": trend_score(spy),
        "iwm_trend": trend_score(iwm),
        "eem_rel_1m": eem_rel_1m,
        "eem_rel_3m": eem_rel_3m,
        "ihsg_rel_1m": ihsg_rel_1m,
        "eem_trend": trend_score(eem),
        "ihsg_trend": trend_score(ihsg),
        "em_rotation_score": em_rotation_score,
        "sector_support_1m": float(sector_support_1m),
        "sector_support_3m": float(sector_support_3m),
        "sector_support_ratio": float(sector_support_ratio),
        "breadth_health": float(breadth_health),
        "breadth_trend_state": breadth_trend_state,
        "narrow_leadership": float(narrow_leadership),
        "eqw_health": float(eqw_health),
        "smallcap_health": float(smallcap_health),
        "escape_route": escape_route,
        **{f"escape_{k.lower()}": v for k, v in escape_scores.items()},
        **{f"sector_{k.lower()}_1m": v for k, v in sector_1m.items()},
    }
    return {k: (float(np.nan_to_num(v, nan=0.0)) if isinstance(v, (int, float, np.floating)) else v) for k, v in features.items()}
