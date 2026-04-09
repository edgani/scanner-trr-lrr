from __future__ import annotations
from pathlib import Path
import io
import re
import pandas as pd
import requests
from config.settings import UNIVERSES_DIR, FOREX_MAJOR_PAIRS, COMMODITY_SYMBOLS
from config.universe_seeds import US_SEED, IHSG_SEED, CRYPTO_SEED

NASDAQ_URL = 'https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt'
IHSG_GITHUB_URL = 'https://github.com/wildangunawan/Dataset-Saham-IDX/raw/refs/heads/master/List%20Emiten/all.csv'
IDX_STOCK_LIST_URLS = [
    'https://www.idx.co.id/en/market-data/stocks-data/stock-list',
    'https://www.idx.co.id/id/data-pasar/data-saham/daftar-saham/',
]
BINANCE_ENDPOINTS = [
    'https://api.binance.com/api/v3/exchangeInfo',
    'https://api1.binance.com/api/v3/exchangeInfo',
    'https://api2.binance.com/api/v3/exchangeInfo',
    'https://api3.binance.com/api/v3/exchangeInfo',
    'https://api4.binance.com/api/v3/exchangeInfo',
]
COINBASE_PRODUCTS_URL = 'https://api.exchange.coinbase.com/products'
KRAKEN_ASSETPAIRS_URL = 'https://api.kraken.com/0/public/AssetPairs'

_EQUITY_EXCLUDE_RE = re.compile(
    r'Warrant| Unit| Rights| Right | Preferred| Preference| Notes| Note | ETN| Fund| ETF| Trust| Depositary| ADR| ADS| Beneficial Interest| Contingent Value Right| CVR| Interest',
    re.IGNORECASE,
)


def universe_path(market: str) -> Path:
    UNIVERSES_DIR.mkdir(parents=True, exist_ok=True)
    return UNIVERSES_DIR / f'{market}_universe.csv'


def _unique(symbols: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in symbols:
        sym = str(raw).strip()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    return out


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


def _session(timeout: int) -> requests.Session:
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0 MarketIntel/1.0'})
    s.request_timeout = timeout
    return s


def refresh_us_universe(timeout: int = 25) -> list[str]:
    s = _session(timeout)
    resp = s.get(NASDAQ_URL, timeout=timeout)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text), sep='|')
    df = df[df['Symbol'].notna()].copy()
    # Max-coverage mode: include all current-trading-day test-issue=N symbols,
    # then let downstream history/tradability filters decide what is actually eligible.
    mask = (df['Test Issue'] == 'N')
    syms = df.loc[mask, 'Symbol'].astype(str).str.strip().str.replace('.', '-', regex=False)
    syms = syms[syms.str.match(r'^[A-Z]{1,5}(?:-[A-Z])?$')]
    return _unique(syms.tolist())


def refresh_ihsg_universe(timeout: int = 25) -> list[str]:
    s = _session(timeout)
    # Preferred source: maintained CSV with ~952 tickers.
    try:
        resp = s.get(IHSG_GITHUB_URL, timeout=timeout)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        codes = df['code'].astype(str).str.upper().str.strip()
        syms = [f'{c}.JK' for c in codes if re.fullmatch(r'[A-Z]{4}', c)]
        syms = _unique(syms)
        if len(syms) >= 900:
            return syms
    except Exception:
        pass
    # Fallback: scrape visible ticker codes from IDX pages.
    symbols: list[str] = []
    for url in IDX_STOCK_LIST_URLS:
        try:
            resp = s.get(url, timeout=timeout)
            if not resp.ok:
                continue
            html = resp.text
            codes = re.findall(r'([A-Z]{4})', html)
            filtered = [f'{code}.JK' for code in codes if code not in {'JSON', 'HTML', 'IDX'}]
            symbols.extend(filtered)
            if len(filtered) > 500:
                break
        except Exception:
            continue
    return _unique(symbols)




def _norm_crypto_base(base: str) -> str:
    base = str(base or '').strip().upper()
    aliases = {
        'XBT': 'BTC',
        'BCC': 'BCH',
    }
    return aliases.get(base, base)


def _coinbase_crypto_universe(s: requests.Session, timeout: int) -> list[str]:
    resp = s.get(COINBASE_PRODUCTS_URL, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    symbols: list[str] = []
    for row in data:
        quote = str(row.get('quote_currency') or '').upper()
        status = str(row.get('status') or '').lower()
        trading_disabled = bool(row.get('trading_disabled', False))
        if quote != 'USD' or trading_disabled or status not in {'online', ''}:
            continue
        base = _norm_crypto_base(row.get('base_currency'))
        if base and re.fullmatch(r'[A-Z0-9]{2,20}', base):
            symbols.append(f'{base}-USD')
    return _unique(symbols)


def _kraken_crypto_universe(s: requests.Session, timeout: int) -> list[str]:
    resp = s.get(KRAKEN_ASSETPAIRS_URL, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    result = data.get('result', {}) if isinstance(data, dict) else {}
    symbols: list[str] = []
    for _, row in result.items():
        wsname = str(row.get('wsname') or '')
        if '/USD' not in wsname:
            continue
        base = _norm_crypto_base(wsname.split('/')[0])
        if base and re.fullmatch(r'[A-Z0-9]{2,20}', base):
            symbols.append(f'{base}-USD')
    return _unique(symbols)


def refresh_crypto_universe(timeout: int = 25) -> list[str]:
    s = _session(timeout)
    # Prefer Binance USDT spot universe when reachable.
    for url in BINANCE_ENDPOINTS:
        try:
            resp = s.get(url, timeout=timeout)
            if resp.status_code == 451:
                continue
            resp.raise_for_status()
            data = resp.json()
            symbols: list[str] = []
            for row in data.get('symbols', []):
                if row.get('status') != 'TRADING':
                    continue
                if row.get('quoteAsset') != 'USDT':
                    continue
                base = _norm_crypto_base(row.get('baseAsset'))
                if base and re.fullmatch(r'[A-Z0-9]{2,20}', base):
                    symbols.append(f'{base}-USD')
            out = _unique(symbols)
            if out:
                return out
        except Exception:
            continue
    # Fallback 1: Coinbase spot USD products.
    try:
        out = _coinbase_crypto_universe(s, timeout)
        if out:
            return out
    except Exception:
        pass
    # Fallback 2: Kraken USD tradable pairs.
    try:
        out = _kraken_crypto_universe(s, timeout)
        if out:
            return out
    except Exception:
        pass
    # Final fallback keeps app usable even when every exchange blocks the host.
    return load_universe('crypto') or CRYPTO_SEED


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
