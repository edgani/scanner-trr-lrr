from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(module: str, *args: str, env: dict[str, str] | None = None) -> None:
    cmd = [sys.executable, '-m', module, *args]
    print('RUN', ' '.join(cmd))
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)
    subprocess.run(cmd, cwd=str(ROOT.parent), check=True, env=merged_env)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--skip-yahoo', action='store_true')
    ap.add_argument('--skip-crypto', action='store_true')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--macro-root', help='Extracted MacroRegime v33 root folder (contains .cache/latest_snapshot.json)')
    args = ap.parse_args()

    env = {'SCANNER_MACRO_ROOT': args.macro_root} if args.macro_root else None
    run('scanner_vfinal.builders.export_brain_v33', env=env)
    run('scanner_vfinal.builders.refresh_universes', env=env)
    if not args.skip_yahoo:
        yahoo_args = [] if args.limit is None else ['--limit', str(args.limit)]
        run('scanner_vfinal.builders.update_history_yahoo', *yahoo_args, env=env)
    if not args.skip_crypto:
        crypto_args = [] if args.limit is None else ['--limit', str(args.limit)]
        run('scanner_vfinal.builders.update_history_coingecko', *crypto_args, env=env)
    run('scanner_vfinal.builders.build_pass1_features', env=env)
    run('scanner_vfinal.builders.build_pass2_snapshots', env=env)
