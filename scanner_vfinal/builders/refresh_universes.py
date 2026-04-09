from __future__ import annotations

import io
from pathlib import Path
import requests
import pandas as pd

from scanner_vfinal.config.symbol_map import FOREX_SYMBOLS, COMMODITY_SYMBOLS
from scanner_vfinal.config.asset_buckets import bucket_for

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_DIR = ROOT / "data" / "universes"

NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqtraded.txt"
IHSG_URL = "https://raw.githubusercontent.com/wildangunawan/Dataset-Saham-IDX/master/List%20Emiten/all.csv"
COINGECKO_MARKETS = "https://api.coingecko.com/api/v3/coins/markets"


def _save(df: pd.DataFrame, market: str) -> None:
    df = df.drop_duplicates(subset=['symbol']).sort_values('symbol')
    df['bucket'] = [bucket_for(market, s, n) for s, n in zip(df['symbol'], df['name'])]
    UNIVERSE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(UNIVERSE_DIR / f"{market}_universe.csv", index=False)
    print(f"saved {market}: {len(df)}")


def refresh_us() -> None:
    r = requests.get(NASDAQ_URL, timeout=60)
    r.raise_for_status()
    lines = r.text.splitlines()
    # parse pipe-delimited txt
    rows = []
    cols = lines[0].split('|')
    for line in lines[1:]:
        parts = line.split('|')
        if len(parts) != len(cols) or parts[0] == 'File Creation Time':
            continue
        row = dict(zip(cols, parts))
        sym = row.get('Symbol', '')
        if not sym or '$' in sym or '^' in sym or '/' in sym:
            continue
        # keep common tradable equities-like names, exclude test/issues/ETFs where obvious
        if row.get('Test Issue') == 'Y':
            continue
        if row.get('ETF', 'N') == 'Y':
            continue
        if sym.endswith(('W', 'U', 'R')) and len(sym) <= 5:
            continue
        rows.append({'symbol': sym, 'name': row.get('Security Name', sym), 'market': 'us'})
    _save(pd.DataFrame(rows), 'us')


def refresh_ihsg() -> None:
    r = requests.get(IHSG_URL, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    col = next((c for c in df.columns if c.lower() in {'ticker', 'symbol', 'code'}), df.columns[0])
    name_col = next((c for c in df.columns if c.lower() in {'name', 'company', 'company_name'}), col)
    out = pd.DataFrame({'symbol': df[col].astype(str).str.strip().str.upper() + '.JK', 'name': df[name_col].astype(str), 'market': 'ihsg'})
    _save(out, 'ihsg')


def refresh_forex() -> None:
    out = pd.DataFrame({'symbol': list(FOREX_SYMBOLS.values()), 'name': list(FOREX_SYMBOLS.keys()), 'market': 'forex'})
    _save(out, 'forex')


def refresh_commodities() -> None:
    out = pd.DataFrame({'symbol': list(COMMODITY_SYMBOLS.values()), 'name': list(COMMODITY_SYMBOLS.keys()), 'market': 'commodities'})
    _save(out, 'commodities')


def refresh_crypto(per_page: int = 250, pages: int = 8) -> None:
    sess = requests.Session()
    rows = []
    for page in range(1, pages + 1):
        resp = sess.get(COINGECKO_MARKETS, params={
            'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': per_page, 'page': page,
            'sparkline': 'false', 'price_change_percentage': '24h',
        }, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        for item in data:
            sym = str(item.get('symbol', '')).upper() + '-USD'
            rows.append({'symbol': sym, 'name': str(item.get('name', sym)), 'coingecko_id': item.get('id', ''), 'market': 'crypto'})
    _save(pd.DataFrame(rows), 'crypto')


def main() -> None:
    refresh_us()
    refresh_ihsg()
    refresh_forex()
    refresh_commodities()
    refresh_crypto()


if __name__ == '__main__':
    main()
