from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scanner.universe_loader import refresh_market_universe, save_universe, load_universe
from config.settings import MARKET_ORDER

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--market', choices=MARKET_ORDER + ['all'], default='all')
    args = parser.parse_args()
    markets = MARKET_ORDER if args.market == 'all' else [args.market]
    for market in markets:
        before = load_universe(market)
        symbols = refresh_market_universe(market)
        path = save_universe(market, symbols)
        delta = len(symbols) - len(before)
        sign = '+' if delta >= 0 else ''
        print(f'{market}: saved {len(symbols)} symbols ({sign}{delta} vs previous {len(before)}) -> {path}')

if __name__ == '__main__':
    main()
