from __future__ import annotations

import compileall
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ok = compileall.compile_dir(ROOT / "scanner_vfinal", quiet=1)
ok = compileall.compile_dir(ROOT / "macroregime_v33", quiet=1) and ok
print("compile_ok=", ok)
raise SystemExit(0 if ok else 1)
