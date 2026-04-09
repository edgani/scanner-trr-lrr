from __future__ import annotations
from typing import Dict, List

from utils.math_utils import clamp01


class PolicyPlaybookEngine:
    def run(self, macro: Dict[str, float], market: Dict[str, float], plumbing: Dict[str, float], shock_state: str) -> List[Dict[str, object]]:
        oil_shock = max(0.0, float(macro.get("oil_3m", 0.0)))
        dollar = max(0.0, float(market.get("dxy_1m", 0.0)))
        smallcap_failure = max(0.0, -float(market.get("iwm_rel_1m", 0.0)))
        long_end = float(plumbing.get("long_end_pressure", 0.5))
        breadth_damage = clamp01(0.5 - 0.5 * float(market.get("rsp_rel_1m", 0.0)))
        growth_stress = clamp01(0.5 - 0.5 * float(macro.get("growth_momentum", 0.0)))

        out: List[Dict[str, object]] = []

        pain_before_relief = clamp01(0.35 * long_end + 0.20 * breadth_damage + 0.20 * growth_stress + 0.15 * smallcap_failure + 0.10 * dollar)
        out.append({
            "name": "Pain-before-relief refinancing playbook",
            "evidence_score": clamp01(0.55 * long_end + 0.25 * growth_stress + 0.20 * smallcap_failure),
            "hypothesis_score": pain_before_relief,
            "description": "Long-end pressure, growth stress, and weak internals raise the odds that financial-pain thresholds eventually favor relief messaging or friendlier debt-management optics.",
            "invalidators": [
                "Long-end pressure keeps worsening without policy response",
                "Credit and breadth continue to deteriorate together",
                "Inflation shock accelerates faster than growth relief odds",
            ],
        })

        war_then_deescalation = clamp01(0.45 * oil_shock + 0.20 * dollar + 0.20 * breadth_damage + 0.15 * (1.0 if shock_state in {"stress", "shock"} else 0.0))
        out.append({
            "name": "War-shock then de-escalation branch",
            "evidence_score": clamp01(0.60 * oil_shock + 0.20 * dollar + 0.20 * breadth_damage),
            "hypothesis_score": war_then_deescalation,
            "description": "Energy shock supports stagflation trades first, but rising pain can later make partial de-escalation or relief narratives much more market-relevant.",
            "invalidators": [
                "Oil keeps extending without pause",
                "Dollar pressure intensifies and breadth never stabilizes",
                "Small-cap and credit failure deepen together",
            ],
        })

        tariff_negotiation = clamp01(0.35 * dollar + 0.25 * long_end + 0.20 * smallcap_failure + 0.20 * breadth_damage)
        out.append({
            "name": "Tariff-style pressure then negotiation relief",
            "evidence_score": clamp01(0.40 * dollar + 0.35 * smallcap_failure + 0.25 * long_end),
            "hypothesis_score": tariff_negotiation,
            "description": "Rising dollar, weak small caps, and long-end pain can resemble prior pressure cycles where later negotiation moderation triggers tactical relief.",
            "invalidators": [
                "Escalation rhetoric keeps compounding",
                "Small caps remain unable to stabilize",
                "Long-end and vol stress reinforce each other",
            ],
        })

        out.sort(key=lambda x: float(x["hypothesis_score"]), reverse=True)
        return out
