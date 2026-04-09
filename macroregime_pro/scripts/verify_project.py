from __future__ import annotations

import importlib
import json
import sys
import py_compile
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
]

FILES = [
    ROOT / "app.py",
]


def main() -> None:
    loaded = []
    compiled = []
    for name in MODULES:
        importlib.import_module(name)
        loaded.append(name)
    for file_path in FILES:
        py_compile.compile(str(file_path), doraise=True)
        compiled.append(str(file_path.name))

    smoke = {}
    try:
        mod = importlib.import_module('orchestration.build_snapshot')
        snap = mod.build_snapshot()
        smoke = {
            'build_snapshot_ok': True,
            'top_level_keys': sorted(list((snap or {}).keys()))[:20],
            'runtime_mode': (snap or {}).get('meta', {}).get('runtime_mode'),
        }
    except Exception as exc:
        smoke = {
            'build_snapshot_ok': False,
            'error_type': type(exc).__name__,
            'error': str(exc),
        }
    print(json.dumps({'imports_ok': loaded, 'compiled_ok': compiled, 'smoke_test': smoke}, indent=2))


if __name__ == "__main__":
    main()
