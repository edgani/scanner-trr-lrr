from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "macroregime_v33" / ".cache" / "latest_snapshot.json"
DST = ROOT / "scanner_vfinal" / "data" / "macro" / "latest_macro_snapshot.json"


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Missing macro snapshot: {SRC}")
    raw = json.loads(SRC.read_text(encoding="utf-8"))
    shared = raw.get("shared_core", {})
    regime = shared.get("regime", {})
    out = {
        "generated_at": raw.get("meta", {}).get("generated_at"),
        "current_quad": regime.get("current_quad"),
        "next_quad": regime.get("next_quad"),
        "monthly_quad": regime.get("monthly_quad"),
        "monthly_next_quad": regime.get("monthly_next_quad"),
        "execution_mode": shared.get("execution_mode", {}),
        "weather": shared.get("weather", {}),
        "shock": shared.get("shock", {}),
        "health": shared.get("health", {}),
        "risk_summary": shared.get("risk_summary", {}),
        "next_path": shared.get("next_path", {}),
        "safe_harbor": shared.get("safe_harbor"),
        "best_beneficiary": shared.get("best_beneficiary"),
        "status_ribbon": shared.get("status_ribbon", {}),
        "flow_stack": shared.get("flow_stack", {}),
        "checklists": shared.get("asset_checklists", {}),
        "top_drivers": shared.get("top_drivers", []),
        "top_risks": shared.get("top_risks", []),
    }
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {DST}")


if __name__ == "__main__":
    main()
