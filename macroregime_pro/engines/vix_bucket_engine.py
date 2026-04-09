from __future__ import annotations
from typing import Dict


class VIXBucketEngine:
    def __init__(self, investable_hi: float = 19.0, chop_hi: float = 29.0):
        self.investable_hi = investable_hi
        self.chop_hi = chop_hi

    def run(self, deriv_vol: Dict[str, float]) -> Dict[str, object]:
        vix_last = float(deriv_vol.get("vix_last", 0.0))
        iv_rv = float(deriv_vol.get("iv_rv_ratio", 1.0))
        vol_regime = str(deriv_vol.get("vol_regime", "normal"))
        tail_hedge_bid = float(deriv_vol.get("tail_hedge_bid", 0.5))

        if vix_last <= 0:
            bucket = "Unknown"
            risk_mode = "Normal"
        elif vix_last < self.investable_hi:
            bucket = "Investable"
            risk_mode = "Normal"
        elif vix_last < self.chop_hi:
            bucket = "Chop"
            risk_mode = "Reduced"
        else:
            bucket = "Defensive"
            risk_mode = "Defensive"

        notes = []
        if bucket == "Investable":
            notes.append("Vol regime relatif tenang; pullback lebih layak dibeli bila signal searah.")
        elif bucket == "Chop":
            notes.append("Vol sedang; lebih cocok buy low / sell high dan kurangi kejar breakout lemah.")
        elif bucket == "Defensive":
            notes.append("Vol tinggi; utamakan capital preservation dan tunggu confirm lebih kuat.")
        if iv_rv > 1.35:
            notes.append("Implied vol premium tinggi; market lebih mahal membayar protection.")
        if vol_regime in {"elevated", "high"}:
            notes.append(f"Derivatives vol regime {vol_regime}; sizing lebih disiplin.")
        if tail_hedge_bid >= 0.65:
            notes.append("Tail-hedge bid tinggi; market sedang lebih sensitif ke left-tail shock.")

        return {
            "bucket": bucket,
            "risk_mode": risk_mode,
            "vix_last": vix_last,
            "iv_rv_ratio": iv_rv,
            "vol_regime": vol_regime,
            "tail_hedge_bid": tail_hedge_bid,
            "notes": notes,
        }
