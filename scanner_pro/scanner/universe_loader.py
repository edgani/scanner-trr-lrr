from __future__ import annotations
from pathlib import Path
import re
import pandas as pd
import requests
from config.settings import UNIVERSES_DIR, FOREX_MAJOR_PAIRS, COMMODITY_SYMBOLS
from config.universe_seeds import US_SEED, IHSG_SEED, CRYPTO_SEED

IDX_STOCK_LIST_URLS = [
    'https://www.idx.co.id/en/market-data/stocks-data/stock-list',
    'https://www.idx.co.id/id/data-pasar/data-saham/daftar-saham/',
]
NASDAQ_URL = 'https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt'
BINANCE_URL = 'https://api.binance.com/api/v3/exchangeInfo'

def universe_path(market: str) -> Path:
    UNIVERSES_DIR.mkdir(parents=True, exist_ok=True)
    return UNIVERSES_DIR / f'{market}_universe.csv'

def _unique(symbols: list[str]) -> list[str]:
    return list(dict.fromkeys([str(x).strip() for x in symbols if str(x).strip()]))

def save_universe(market: str, symbols: list[str]) -> Path:
    path = universe_path(market)
    pd.DataFrame({'symbol': _unique(symbols)}).to_csv(path, index=False)
    return path

def load_universe(market: str) -> list[str]:
    path = universe_path(market)
    if path.exists():
        df = pd.read_csv(path)
        symbols = _unique(df.get('symbol', pd.Series(dtype=str)).tolist())
        if symbols:
            return symbols
    if market == 'us':
        return US_SEED
    if market == 'ihsg':
        return IHSG_SEED
    if market == 'crypto':
        return CRYPTO_SEED
    if market == 'forex':
        return FOREX_MAJOR_PAIRS
    if market == 'commodities':
        return COMMODITY_SYMBOLS
    return []

def refresh_us_universe(timeout: int = 25) -> list[str]:
    text = requests.get(NASDAQ_URL, timeout=timeout).text
    lines = [x for x in text.splitlines() if '|' in x]
    symbols: list[str] = []
    for line in lines[1:]:
        parts = line.split('|')
        if not parts or parts[0] == 'File Creation Time':
            continue
        sym = parts[1] if parts[0] == 'Y' else parts[0]
        sym = sym.strip()
        if sym and sym.isascii() and '$' not in sym and '.' not in sym and '^' not in sym:
            symbols.append(sym)
    return _unique(symbols)

def refresh_ihsg_universe(timeout: int = 25) -> list[str]:
    symbols: list[str] = []
    for url in IDX_STOCK_LIST_URLS:
        try:
            resp = requests.get(url, timeout=timeout)
        except Exception:
            continue
        if not resp.ok:
            continue
        html = resp.text
        codes = re.findall(r'\b([A-Z]{4})\b', html)
        filtered = [f'{code}.JK' for code in codes if code not in {'JSON', 'HTML', 'IDX'}]
        symbols.extend(filtered)
        if len(filtered) > 500:
            break
    return _unique(symbols)

def refresh_crypto_universe(timeout: int = 25) -> list[str]:
    data = requests.get(BINANCE_URL, timeout=timeout).json()
    symbols: list[str] = []
    for row in data.get('symbols', []):
        if row.get('status') != 'TRADING':
            continue
        if row.get('quoteAsset') != 'USDT':
            continue
        base = str(row.get('baseAsset') or '').strip()
        if base:
            symbols.append(f'{base}-USD')
    return _unique(symbols)

def refresh_market_universe(market: str) -> list[str]:
    if market == 'us':
        return refresh_us_universe()
    if market == 'ihsg':
        return refresh_ihsg_universe()
    if market == 'crypto':
        return refresh_crypto_universe()
    if market == 'forex':
        return FOREX_MAJOR_PAIRS
    if market == 'commodities':
        return COMMODITY_SYMBOLS
    raise ValueError(f'Unknown market: {market}')
