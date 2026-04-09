from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRAIN_FILE = ROOT / "data" / "macro" / "latest_macro_snapshot.json"


def load_brain() -> dict[str, Any]:
    if not BRAIN_FILE.exists():
        return {}
    return json.loads(BRAIN_FILE.read_text(encoding="utf-8"))


def current_quad(brain: dict[str, Any]) -> str:
    return str(brain.get("current_quad") or brain.get("status_ribbon", {}).get("current_quad") or "unknown")


def next_route(brain: dict[str, Any]) -> dict[str, Any]:
    return brain.get("next_path", {})


def execution_mode(brain: dict[str, Any]) -> str:
    mode = brain.get("execution_mode", {})
    if isinstance(mode, dict):
        return str(mode.get("mode") or mode.get("label") or "balanced")
    return str(mode or "balanced")


def crash_state(brain: dict[str, Any]) -> str:
    risk = brain.get("risk_summary", {}) or brain.get("status_ribbon", {})
    return str(risk.get("crash") or risk.get("crash_state") or "calm")


def bucket_policy(brain: dict[str, Any], market: str) -> dict[str, set[str]]:
    # Best-effort policy map from current quad/route until a richer explicit export is added.
    quad = current_quad(brain)
    market = market.lower()
    supportive: set[str] = set()
    hostile: set[str] = set()
    next_play: set[str] = set()
    if quad == "Q3":
        supportive |= {"precious", "energy", "energy_exporter", "usd_major", "jpy_safe_haven", "btc_quality"}
        hostile |= {"small_beta", "high_beta", "carry_beta", "meme_beta"}
        next_play |= {"quality_growth", "banks", "majors", "infra"}
    elif quad == "Q4":
        supportive |= {"precious", "jpy_safe_haven", "safe_haven_fx", "banks", "btc_quality"}
        hostile |= {"small_beta", "high_beta", "carry_beta", "commodity_fx", "meme_beta"}
        next_play |= {"energy", "quality_growth", "majors"}
    elif quad == "Q2":
        supportive |= {"cyclical", "small_beta", "commodity_fx", "energy", "majors"}
        hostile |= {"precious", "safe_haven_fx"}
        next_play |= {"banks", "quality_growth", "infra"}
    else:  # Q1 or unknown
        supportive |= {"quality_growth", "financials", "majors", "infra"}
        hostile |= {"precious", "safe_haven_fx"}
        next_play |= {"energy", "cyclical", "banks"}
    # crude market-specific trims
    if market == "forex":
        supportive |= {"usd_major", "jpy_safe_haven", "commodity_fx", "safe_haven_fx", "carry_beta", "em_fx"}
    return {"supportive": supportive, "hostile": hostile, "next": next_play}
