from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(module: str, *args: str) -> None:
    cmd = [sys.executable, '-m', module, *args]
    print('RUN', ' '.join(cmd))
    subprocess.run(cmd, cwd=str(ROOT.parent), check=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--skip-yahoo', action='store_true')
    ap.add_argument('--skip-crypto', action='store_true')
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()

    run('scanner_vfinal.builders.export_brain_v33')
    run('scanner_vfinal.builders.refresh_universes')
    if not args.skip_yahoo:
        yahoo_args = [] if args.limit is None else ['--limit', str(args.limit)]
        run('scanner_vfinal.builders.update_history_yahoo', *yahoo_args)
    if not args.skip_crypto:
        crypto_args = [] if args.limit is None else ['--limit', str(args.limit)]
        run('scanner_vfinal.builders.update_history_coingecko', *crypto_args)
    run('scanner_vfinal.builders.build_pass1_features')
    run('scanner_vfinal.builders.build_pass2_snapshots')
