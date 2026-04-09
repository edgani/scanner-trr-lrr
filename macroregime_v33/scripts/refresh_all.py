from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse

from data.universe_loader import get_backend_universe, get_manifest_repo
from data.price_loader import load_price_bundle
from orchestration.build_snapshot import build_snapshot
from config.settings import DEFAULT_PRICE_PERIOD


def main() -> None:
    parser = argparse.ArgumentParser(description='Refresh local history and rebuild latest snapshot.')
    parser.add_argument('--markets', nargs='+', default=['us', 'ihsg', 'fx', 'commodities', 'crypto'])
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    universe = get_backend_universe()
    symbols: list[str] = []
    for market in args.markets:
        for sym in universe.get(str(market).lower(), []):
            if sym not in symbols:
                symbols.append(sym)
    if args.limit and args.limit > 0:
        symbols = symbols[:args.limit]
    meta = load_price_bundle(symbols, period=DEFAULT_PRICE_PERIOD, force_refresh=True, prefer_local_history=True).get('meta', {})
    snap = build_snapshot(force_refresh=False, prefer_saved=False, compact_mode=True)
    print({
        'history_requested': meta.get('requested'),
        'history_loaded': meta.get('loaded'),
        'snapshot_generated_at': snap.get('meta', {}).get('generated_at'),
        'manifests': get_manifest_repo(),
    })


if __name__ == '__main__':
    main()
