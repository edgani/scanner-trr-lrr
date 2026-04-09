from __future__ import annotations
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parent

cmds = [
    ['python', str(ROOT / 'macroregime_pro' / 'scripts' / 'verify_project.py')],
    ['python', str(ROOT / 'scanner_pro' / 'scripts' / 'verify_project.py')],
]
for cmd in cmds:
    print('RUN', ' '.join(cmd))
    subprocess.run(cmd, check=True)
print('All verify steps passed.')
