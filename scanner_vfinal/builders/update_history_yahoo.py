from __future__ import annotations

import argparse
from pathlib import Path
import re

import pandas as pd
import yfinance as yf

from scanner_vfinal.scanner.registry import load_universe

ROOT = Path(__file__).resolve().parents[1]
HISTORY_DIR = ROOT / 'data' / 'history'


def safe_name(symbol: str) -> str:
    return re.sub(r'[^A-Za-z0-9._-]+', '_', symbol)


def update_market(market: str) -> None:
    if market == 'crypto':
        return
    uni = load_universe(market)
    out_dir = HISTORY_DIR / market
    out_dir.mkdir(parents=True, exist_ok=True)
    for _, row in uni.iterrows():
        symbol = str(row['symbol'])
        try:
            df = yf.download(symbol, period='max', interval='1d', auto_adjust=False, actions=True, progress=False, threads=False)
            if df is None or df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            p = out_dir / f"{safe_name(symbol)}.csv.gz"
            df.reset_index().to_csv(p, index=False, compression='gzip')
        except Exception as exc:
            print(f"history fail {market} {symbol}: {exc}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--market', action='append', choices=['us', 'ihsg', 'forex', 'commodities'])
    args = ap.parse_args()
    markets = args.market or ['us', 'ihsg', 'forex', 'commodities']
    for m in markets:
        update_market(m)


if __name__ == '__main__':
    main()
