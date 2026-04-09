from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
from typing import Iterable

from config.settings import DEFAULT_PRICE_PERIOD
from config.universes import FULL_UNIVERSE
from data.price_loader import load_price_bundle
from data.universe_loader import get_backend_universe, get_manifest_repo


MARKET_MAP = get_backend_universe()


def _symbols_for(markets: Iterable[str]) -> list[str]:
    picked: list[str] = []
    for market in markets:
        key = market.lower().strip()
        if key == 'all':
            for sym in FULL_UNIVERSE:
                if sym not in picked:
                    picked.append(sym)
            continue
        for sym in MARKET_MAP.get(key, []):
            if sym not in picked:
                picked.append(sym)
    return picked


def main() -> None:
    parser = argparse.ArgumentParser(description='Bootstrap or update local full-history cache for MacroRegime.')
    parser.add_argument('--markets', nargs='+', default=['all'], help='us ihsg fx commodities crypto or all')
    parser.add_argument('--force-refresh', action='store_true', help='Re-hit provider and merge fresh data into local history store.')
    parser.add_argument('--limit', type=int, default=0, help='Optional cap for requested symbols after universe selection.')
    args = parser.parse_args()

    symbols = _symbols_for(args.markets)
    if args.limit and args.limit > 0:
        symbols = symbols[:args.limit]
    bundle = load_price_bundle(symbols, period=DEFAULT_PRICE_PERIOD, force_refresh=args.force_refresh, prefer_local_history=True)
    meta = bundle.get('meta', {})
    print({
        'requested': meta.get('requested'),
        'loaded': meta.get('loaded'),
        'missing': meta.get('missing'),
        'history_store_hits': meta.get('history_store_hits'),
        'history_store_misses': meta.get('history_store_misses'),
        'fetched_from_provider': meta.get('fetched_from_provider'),
        'history_mode': meta.get('history_mode'),
        'manifests': get_manifest_repo(),
    })


if __name__ == '__main__':
    main()
