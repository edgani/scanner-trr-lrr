from __future__ import annotations
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent

def run(cmd: list[str], check: bool=True):
    print('RUN', ' '.join(cmd))
    return subprocess.run(cmd, cwd=ROOT, check=check)

run(['python', 'build_daily_local.py'])
paths = [
    'scanner_pro/data/universes',
    'scanner_pro/data/scans',
    'scanner_pro/data/macro/latest_snapshot.json',
    'macroregime_pro/.cache/latest_snapshot.json',
    'macroregime_pro/.cache/latest_snapshot_manifest.json',
]
run(['git', 'add'] + paths)
status = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True, check=True)
if status.stdout.strip():
    msg = 'daily refresh ' + datetime.now().strftime('%Y-%m-%d %H:%M')
    run(['git', 'commit', '-m', msg], check=False)
    run(['git', 'push'], check=False)
else:
    print('No changes to commit.')
