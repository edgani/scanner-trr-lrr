from __future__ import annotations

from scanner_vfinal.scanner.registry import load_universe, save_universe


MARKETS = ['us', 'ihsg', 'forex', 'commodities', 'crypto']


if __name__ == '__main__':
    for market in MARKETS:
        df = load_universe(market)
        save_universe(market, df)
        print(f'{market}: {len(df)}')
