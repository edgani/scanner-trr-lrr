from __future__ import annotations

import argparse
import importlib
import json
import os
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODULES = [
    "config.settings",
    "data.price_loader",
    "data.history_store",
    "data.snapshot_store",
    "orchestration.build_snapshot",
    "engines.shared_core_engine",
    "utils.ranking_utils",
    "data.universe_loader",
]

REQUIRED_TOP_LEVEL = {
    "meta", "shared_core", "master_routes", "master_opportunities",
    "position_lifecycle", "home_summary", "scenario_lab",
    "us", "ihsg", "fx", "commodities", "crypto", "diagnostics",
}

REQUIRED_MARKET_KEYS = {
    "macro_vs_market", "transmission", "asset_checklist", "setups_now",
    "forward_radar", "market_hub", "strong_weak", "execution",
    "next_path", "flow_stack", "catalyst_overlay",
    "top_opportunities_now", "top_opportunities_next", "route_branch",
}


def _compile_all_py() -> list[str]:
    compiled = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(part.startswith(".") and part not in {".streamlit"} for part in path.parts):
            continue
        py_compile.compile(str(path), doraise=True)
        compiled.append(str(path.relative_to(ROOT)))
    return compiled


def _validate_snapshot_shape(snapshot: dict) -> dict:
    missing_top = sorted(REQUIRED_TOP_LEVEL - set(snapshot.keys()))
    market_reports = {}
    for market in ["us", "ihsg", "fx", "commodities", "crypto"]:
        section = snapshot.get(market, {}) or {}
        missing_keys = sorted(REQUIRED_MARKET_KEYS - set(section.keys()))
        market_reports[market] = {
            "missing_keys": missing_keys,
            "setups_now": len(section.get("setups_now", []) or []),
            "forward_radar": len(section.get("forward_radar", []) or []),
            "top_opportunities_now": len(section.get("top_opportunities_now", []) or []),
            "top_opportunities_next": len(section.get("top_opportunities_next", []) or []),
        }
    return {"missing_top_level": missing_top, "markets": market_reports}


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify MacroRegime project structure and snapshot surface.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any required snapshot fields are missing.")
    parser.add_argument("--allow-live-fetch", action="store_true", help="Do not force MRP_LIVE_FETCH=0 during verification.")
    parser.add_argument("--rebuild-snapshot", action="store_true", help="Rebuild snapshot instead of using saved snapshot when available.")
    args = parser.parse_args()

    if not args.allow_live_fetch:
        os.environ.setdefault("MRP_LIVE_FETCH", "0")

    loaded = []
    for name in MODULES:
        importlib.import_module(name)
        loaded.append(name)

    compiled = _compile_all_py()

    build_mod = importlib.import_module("orchestration.build_snapshot")
    universe_mod = importlib.import_module("data.universe_loader")
    snap = build_mod.build_snapshot(force_refresh=False, prefer_saved=(not args.rebuild_snapshot), compact_mode=True)
    shape = _validate_snapshot_shape(snap)

    report = {
        "imports_ok": loaded,
        "compiled_count": len(compiled),
        "compiled_sample": compiled[:12],
        "snapshot": {
            "build_snapshot_ok": True,
            "top_level_keys": sorted(list((snap or {}).keys())),
            "runtime_mode": (snap or {}).get("meta", {}).get("runtime_mode"),
            "schema": (snap or {}).get("meta", {}).get("schema"),
            "loader_meta": (snap or {}).get("meta", {}).get("loader_meta", {}),
            "history_meta": (snap or {}).get("meta", {}).get("history_meta", {}),
        },
        "shape_audit": shape,
        "manifest_repo": universe_mod.get_manifest_repo(),
    }

    strict_failures = bool(shape["missing_top_level"]) or any(v["missing_keys"] for v in shape["markets"].values())
    report["strict_ok"] = not strict_failures
    print(json.dumps(report, indent=2))

    if args.strict and strict_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
