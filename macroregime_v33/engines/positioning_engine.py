from __future__ import annotations
from typing import Dict


class PositioningEngine:
    def run(self, position: Dict[str, float]) -> Dict[str, object]:
        crowding = float(position.get("crowding_proxy", position.get("crowding", 0.0)))
        concentration = float(position.get("concentration", 0.0))
        squeeze_risk = float(position.get("squeeze_risk_proxy", position.get("squeeze_risk", 0.0)))
        unwind_risk = float(position.get("unwind_risk_proxy", position.get("unwind_risk", 0.0)))
        quality = float(position.get("positioning_quality", 0.5))
        state = str(position.get("crowding_state", "clean"))
        is_proxy_only = bool(position.get("is_proxy_only", True))

        if crowding >= 0.72:
            verdict = "Crowded"
        elif crowding >= 0.55:
            verdict = "Elevated"
        else:
            verdict = "Clean"

        notes = []
        if concentration >= 0.65:
            notes.append("Leadership terlalu terkonsentrasi pada sedikit nama / tema.")
        if unwind_risk >= 0.65:
            notes.append("Risiko unwind naik bila breadth memburuk lagi.")
        if squeeze_risk >= 0.65:
            notes.append("Squeeze / gap risk tinggi; jangan terlalu agresif lawan tape.")
        if quality <= 0.40:
            notes.append("Positioning quality lemah; price action lebih rawan noise dan stop-out.")
        if is_proxy_only:
            notes.append("Positioning ini masih proxy market-internals, belum CFTC/options positioning penuh.")
        if not notes:
            notes.append("Positioning relatif bersih; signal price bisa lebih dipercaya.")

        return {
            "verdict": verdict,
            "crowding": crowding,
            "crowding_proxy": crowding,
            "crowding_state": state,
            "concentration": concentration,
            "positioning_quality": quality,
            "squeeze_risk": squeeze_risk,
            "squeeze_risk_proxy": squeeze_risk,
            "unwind_risk": unwind_risk,
            "unwind_risk_proxy": unwind_risk,
            "notes": notes,
            "is_proxy_only": is_proxy_only,
        }
