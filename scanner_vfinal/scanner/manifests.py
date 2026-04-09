from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIR = ROOT / "data" / "scans"


def write_manifest(market: str, payload: dict[str, Any]) -> None:
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    (SCAN_DIR / f"{market}_scanner_manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
