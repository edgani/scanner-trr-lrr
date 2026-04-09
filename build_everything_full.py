from __future__ import annotations
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parent
steps = [
    ['python', str(ROOT / 'macroregime_pro' / 'scripts' / 'update_full_history.py'), '--markets', 'all', '--force-refresh'],
    ['python', str(ROOT / 'macroregime_pro' / 'scripts' / 'build_live_snapshot.py'), '--force-refresh', '--compact-mode'],
    ['python', str(ROOT / 'sync_macro_to_scanner.py')],
    ['python', str(ROOT / 'scanner_pro' / 'scripts' / 'refresh_universe_snapshots.py'), '--market', 'all'],
    ['python', str(ROOT / 'scanner_pro' / 'scripts' / 'update_full_history.py'), '--market', 'all', '--force-refresh'],
    ['python', str(ROOT / 'scanner_pro' / 'scripts' / 'build_all_snapshots.py')],
]
for step in steps:
    print('RUN', ' '.join(step))
    subprocess.run(step, check=True)
print('Full build complete.')
