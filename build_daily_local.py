from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run(step: list[str], required: bool=True) -> None:
    print('RUN', ' '.join(step))
    try:
        subprocess.run(step, check=True)
    except subprocess.CalledProcessError as e:
        if required:
            raise
        print(f'WARN optional step failed: {e}')

steps = [
    ['python', str(ROOT / 'scanner_pro' / 'scripts' / 'refresh_universe_snapshots.py'), '--market', 'us'],
    ['python', str(ROOT / 'scanner_pro' / 'scripts' / 'refresh_universe_snapshots.py'), '--market', 'ihsg'],
    ['python', str(ROOT / 'scanner_pro' / 'scripts' / 'refresh_universe_snapshots.py'), '--market', 'forex'],
    ['python', str(ROOT / 'scanner_pro' / 'scripts' / 'refresh_universe_snapshots.py'), '--market', 'commodities'],
    ['python', str(ROOT / 'scanner_pro' / 'scripts' / 'refresh_universe_snapshots.py'), '--market', 'crypto'],
    ['python', str(ROOT / 'scanner_pro' / 'scripts' / 'update_full_history.py'), '--market', 'us', '--force-refresh'],
    ['python', str(ROOT / 'scanner_pro' / 'scripts' / 'update_full_history.py'), '--market', 'ihsg', '--force-refresh'],
    ['python', str(ROOT / 'scanner_pro' / 'scripts' / 'update_full_history.py'), '--market', 'forex', '--force-refresh'],
    ['python', str(ROOT / 'scanner_pro' / 'scripts' / 'update_full_history.py'), '--market', 'commodities', '--force-refresh'],
    ['python', str(ROOT / 'scanner_pro' / 'scripts' / 'update_full_history.py'), '--market', 'crypto', '--force-refresh'],
    ['python', str(ROOT / 'scanner_pro' / 'scripts' / 'build_all_snapshots.py')],
]
optional = [
    ['python', str(ROOT / 'macroregime_pro' / 'scripts' / 'update_full_history.py'), '--markets', 'all', '--force-refresh'],
    ['python', str(ROOT / 'macroregime_pro' / 'scripts' / 'build_live_snapshot.py'), '--force-refresh', '--compact-mode'],
    ['python', str(ROOT / 'sync_macro_to_scanner.py')],
]
for s in steps:
    run(s, required=True)
for s in optional:
    run(s, required=False)
print('Local build complete.')
