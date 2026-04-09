from __future__ import annotations
from collections import defaultdict
from typing import Iterable
import pandas as pd
from config.settings import DEFAULT_HISTORY_PERIOD, DEFAULT_INTERVAL, PRICE_CHUNK_SIZE
from .history_store import load_history, save_history, merge_histories

def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[i:i+size] for i in range(0, len(items), size)]

def _normalize_one(df: pd.DataFrame) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    cols = [c for c in ['Open','High','Low','Close','Volume'] if c in df.columns]
    if len(cols) < 4:
        return None
    out = df[cols].dropna(subset=['Close']).copy()
    return out if not out.empty else None

def _extract_symbol_frame(raw: pd.DataFrame, symbol: str) -> pd.DataFrame | None:
    if raw is None or raw.empty:
        return None
    if isinstance(raw.columns, pd.MultiIndex):
        if symbol not in raw.columns.get_level_values(1):
            return None
        sub = raw.xs(symbol, axis=1, level=1, drop_level=True)
        return _normalize_one(sub)
    return _normalize_one(raw)

def _download_chunk(symbols: list[str], *, period: str, interval: str) -> dict[str, pd.DataFrame | None]:
    try:
        import yfinance as yf
    except Exception:
        return {symbol: None for symbol in symbols}
    joined = ' '.join(symbols)
    try:
        raw = yf.download(
            tickers=joined,
            period=period,
            interval=interval,
            auto_adjust=False,
            actions=False,
            progress=False,
            threads=True,
            group_by='ticker',
        )
    except Exception:
        return {symbol: None for symbol in symbols}
    out: dict[str, pd.DataFrame | None] = {}
    for symbol in symbols:
        out[symbol] = _extract_symbol_frame(raw, symbol)
    return out

def update_market_histories(
    market: str,
    symbols: Iterable[str],
    *,
    force_refresh: bool = False,
    period: str = DEFAULT_HISTORY_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> dict:
    symbol_list = list(dict.fromkeys([str(x).strip() for x in symbols if str(x).strip()]))
    chunk_size = PRICE_CHUNK_SIZE.get(market, 25)
    report = {'requested': len(symbol_list), 'updated': 0, 'cached_only': 0, 'failed': [], 'saved': []}
    for batch in _chunks(symbol_list, chunk_size):
        live_map = _download_chunk(batch, period=period, interval=interval)
        for symbol in batch:
            existing = load_history(market, symbol)
            live = live_map.get(symbol)
            if live is None or live.empty:
                if existing is not None and not existing.empty:
                    report['cached_only'] += 1
                else:
                    report['failed'].append(symbol)
                continue
            merged = merge_histories(existing if not force_refresh else None, live)
            if merged is None or merged.empty:
                report['failed'].append(symbol)
                continue
            save_history(market, symbol, merged)
            report['updated'] += 1
            report['saved'].append(symbol)
    report['failed'] = list(dict.fromkeys(report['failed']))
    return report

def load_market_histories(market: str, symbols: Iterable[str]) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        df = load_history(market, symbol)
        if df is not None and not df.empty:
            out[symbol] = df
    return out
