from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from scanner_vfinal.scanner.registry import load_universe

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIR = ROOT / 'data' / 'scans'
JOB_DIR = SCAN_DIR / 'jobs'
ALL_MARKETS = ['us', 'ihsg', 'forex', 'commodities', 'crypto']
YAHOO_MARKETS = ['us', 'ihsg', 'forex', 'commodities']
DEFAULT_BATCH_LIMITS = {
    'us': 300,
    'ihsg': 250,
    'forex': 16,
    'commodities': 3,
    'crypto': 200,
}
DEFAULT_BATCH_DOWNLOAD = {
    'us': 25,
    'ihsg': 25,
    'forex': 8,
    'commodities': 3,
}


def run(module: str, *args: str, env: dict[str, str] | None = None) -> None:
    cmd = [sys.executable, '-m', module, *args]
    print('RUN', ' '.join(cmd))
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)
    subprocess.run(cmd, cwd=str(ROOT.parent), check=True, env=merged_env)


def _state_path(name: str) -> Path:
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    return JOB_DIR / name


def _load_state(name: str) -> dict[str, Any]:
    p = _state_path(name)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding='utf-8'))


def _save_state(name: str, payload: dict[str, Any]) -> None:
    _state_path(name).write_text(json.dumps(payload, indent=2), encoding='utf-8')


def _run_yahoo_market(market: str, refresh_mode: str, env: dict[str, str] | None, resume: bool) -> None:
    universe_len = int(len(load_universe(market)))
    batch_limit = DEFAULT_BATCH_LIMITS[market]
    batch_size = DEFAULT_BATCH_DOWNLOAD[market]
    state_name = f'build_local_snapshot_{market}.json'
    state = _load_state(state_name) if resume else {}
    offset = int(state.get('next_offset', 0) or 0)
    while offset < universe_len:
        run(
            'scanner_vfinal.builders.update_history_yahoo',
            '--market', market,
            '--offset', str(offset),
            '--limit', str(batch_limit),
            '--batch-size', str(batch_size),
            '--refresh-mode', refresh_mode,
            env=env,
        )
        offset += batch_limit
        _save_state(state_name, {
            'market': market,
            'next_offset': offset,
            'universe_count': universe_len,
            'done': offset >= universe_len,
            'refresh_mode': refresh_mode,
        })


def _run_crypto(refresh_mode: str, env: dict[str, str] | None, resume: bool) -> None:
    market = 'crypto'
    universe_len = int(len(load_universe(market)))
    batch_limit = DEFAULT_BATCH_LIMITS[market]
    state_name = 'build_local_snapshot_crypto.json'
    state = _load_state(state_name) if resume else {}
    offset = int(state.get('next_offset', 0) or 0)
    while offset < universe_len:
        run(
            'scanner_vfinal.builders.update_history_coingecko',
            '--offset', str(offset),
            '--limit', str(batch_limit),
            '--refresh-mode', refresh_mode,
            env=env,
        )
        offset += batch_limit
        _save_state(state_name, {
            'market': market,
            'next_offset': offset,
            'universe_count': universe_len,
            'done': offset >= universe_len,
            'refresh_mode': refresh_mode,
        })


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--macro-root', help='Extracted MacroRegime v33 root folder (contains .cache/latest_snapshot.json)')
    ap.add_argument('--skip-yahoo', action='store_true')
    ap.add_argument('--skip-crypto', action='store_true')
    ap.add_argument('--refresh-mode', choices=['missing', 'stale', 'all'], default='stale')
    ap.add_argument('--resume', action='store_true')
    args = ap.parse_args()

    env = {'SCANNER_MACRO_ROOT': args.macro_root} if args.macro_root else None
    run('scanner_vfinal.builders.export_brain_v33', env=env)
    run('scanner_vfinal.builders.refresh_universes', env=env)
    if not args.skip_yahoo:
        for market in YAHOO_MARKETS:
            _run_yahoo_market(market, refresh_mode=args.refresh_mode, env=env, resume=args.resume)
    if not args.skip_crypto:
        _run_crypto(refresh_mode=args.refresh_mode, env=env, resume=args.resume)
    run('scanner_vfinal.builders.build_pass1_features', env=env)
    run('scanner_vfinal.builders.build_pass2_snapshots', env=env)
