from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scanner.price_loader import update_market_histories
from scanner.universe_loader import load_universe
from config.settings import MARKET_ORDER

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--market', choices=MARKET_ORDER + ['all'], default='all')
    parser.add_argument('--force-refresh', action='store_true')
    args = parser.parse_args()
    markets = MARKET_ORDER if args.market == 'all' else [args.market]
    for market in markets:
        symbols = load_universe(market)
        report = update_market_histories(market, symbols, force_refresh=args.force_refresh)
        print(f"{market}: requested={report['requested']} updated={report['updated']} cached_only={report['cached_only']} failed={len(report['failed'])}")

if __name__ == '__main__':
    main()
