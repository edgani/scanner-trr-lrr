from __future__ import annotations

import time
from pathlib import Path
import re

import pandas as pd
import requests

from scanner_vfinal.scanner.registry import load_universe

ROOT = Path(__file__).resolve().parents[1]
HISTORY_DIR = ROOT / 'data' / 'history' / 'crypto'
MARKET_URL = 'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart'


def safe_name(symbol: str) -> str:
    return re.sub(r'[^A-Za-z0-9._-]+', '_', symbol)


def main() -> None:
    uni = load_universe('crypto')
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    sess = requests.Session()
    for _, row in uni.iterrows():
        coin_id = row.get('coingecko_id') or str(row['symbol']).split('-')[0].lower()
        symbol = str(row['symbol'])
        try:
            resp = sess.get(MARKET_URL.format(coin_id=coin_id), params={'vs_currency': 'usd', 'days': 'max', 'interval': 'daily'}, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            prices = data.get('prices', [])
            vols = data.get('total_volumes', [])
            if not prices:
                continue
            df = pd.DataFrame(prices, columns=['ts', 'Close'])
            vol_df = pd.DataFrame(vols, columns=['ts', 'Volume']) if vols else pd.DataFrame(columns=['ts', 'Volume'])
            df['Date'] = pd.to_datetime(df['ts'], unit='ms').dt.date
            if not vol_df.empty:
                vol_df['Date'] = pd.to_datetime(vol_df['ts'], unit='ms').dt.date
                df = df.merge(vol_df[['Date', 'Volume']], on='Date', how='left')
            df['Open'] = df['Close']
            df['High'] = df['Close']
            df['Low'] = df['Close']
            out = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
            out.to_csv(HISTORY_DIR / f"{safe_name(symbol)}.csv.gz", index=False, compression='gzip')
            time.sleep(1.3)
        except Exception as exc:
            print(f"crypto history fail {symbol}: {exc}")


if __name__ == '__main__':
    main()
