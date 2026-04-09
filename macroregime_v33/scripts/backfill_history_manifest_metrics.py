from __future__ import annotations

import argparse

from data.history_store import read_manifest, load_history, update_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description='Rebuild history manifest summary metrics from cached symbol histories.')
    parser.add_argument('--limit', type=int, default=0, help='Optional max number of symbols to rebuild.')
    args = parser.parse_args()

    manifest = read_manifest() or {}
    symbols = sorted((manifest.get('symbols', {}) or {}).keys())
    if args.limit and args.limit > 0:
        symbols = symbols[:args.limit]

    rebuilt = 0
    for symbol in symbols:
        series = load_history(symbol)
        if series.empty:
            continue
        update_manifest(symbol, series)
        rebuilt += 1
    print({'rebuilt': rebuilt, 'scanned_symbols': len(symbols)})


if __name__ == '__main__':
    main()
