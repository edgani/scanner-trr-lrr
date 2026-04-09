from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_module(module: str, *extra: str) -> None:
    cmd = [sys.executable, '-m', module, *extra]
    print('RUN:', ' '.join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def main() -> None:
    run_module('export_scanner_brain')
    run_module('scanner_vfinal.builders.refresh_universes')
    run_module('scanner_vfinal.builders.update_history_yahoo', '--market', 'us', '--market', 'ihsg', '--market', 'forex', '--market', 'commodities')
    run_module('scanner_vfinal.builders.update_history_coingecko')
    run_module('scanner_vfinal.builders.build_pass1_features')
    run_module('scanner_vfinal.builders.build_pass2_snapshots')


if __name__ == '__main__':
    main()
