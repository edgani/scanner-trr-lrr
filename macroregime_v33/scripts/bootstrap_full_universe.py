from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json

from data.universe_loader import get_manifest_repo, get_backend_universe
from data.price_loader import load_price_bundle
from orchestration.build_snapshot import build_snapshot
from config.settings import DEFAULT_PRICE_PERIOD


def main() -> None:
    parser = argparse.ArgumentParser(description='After manifests exist, hydrate history and build a fresh snapshot.')
    parser.add_argument('--markets', nargs='+', default=['us', 'ihsg', 'crypto'])
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--force-refresh', action='store_true')
    args = parser.parse_args()

    universe = get_backend_universe()
    symbols: list[str] = []
    for market in args.markets:
        for sym in universe.get(str(market).lower(), []):
            if sym not in symbols:
                symbols.append(sym)
    if args.limit and args.limit > 0:
        symbols = symbols[:args.limit]

    price_meta = load_price_bundle(symbols, period=DEFAULT_PRICE_PERIOD, force_refresh=args.force_refresh, prefer_local_history=True).get('meta', {})
    snap = build_snapshot(force_refresh=False, prefer_saved=False, compact_mode=True)
    print(json.dumps({
        'manifest_repo': get_manifest_repo(),
        'history_meta': price_meta,
        'snapshot_generated_at': snap.get('meta', {}).get('generated_at'),
        'snapshot_schema': snap.get('meta', {}).get('schema'),
    }, indent=2))


if __name__ == '__main__':
    main()
