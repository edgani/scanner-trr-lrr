from __future__ import annotations
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
src = ROOT / 'macroregime_pro' / '.cache' / 'latest_snapshot.json'
dst = ROOT / 'scanner_pro' / 'data' / 'macro' / 'latest_snapshot.json'
dst.parent.mkdir(parents=True, exist_ok=True)

if not src.exists():
    raise SystemExit(f'Macro snapshot not found: {src}')
shutil.copy2(src, dst)
print(f'Synced macro snapshot -> {dst}')
