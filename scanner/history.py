from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HISTORY_DIR = ROOT / 'data' / 'history'


def safe_name(symbol: str) -> str:
    return re.sub(r'[^A-Za-z0-9._:-]+', '_', str(symbol))


def history_path(market: str, symbol: str) -> Path:
    return HISTORY_DIR / market / f'{safe_name(symbol)}.csv.gz'


def load_history(market: str, symbol: str) -> pd.DataFrame | None:
    p = history_path(market, symbol)
    if not p.exists():
        return None
    df = pd.read_csv(p)
    if df.empty:
        return None
    date_col = 'Date' if 'Date' in df.columns else df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], utc=False, errors='coerce')
    df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()
    df.attrs['symbol'] = symbol
    df.attrs['market'] = market
    return df


REQUIRED_OHLC = ['Open', 'High', 'Low', 'Close']


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename_map = {c: c.title() for c in out.columns}
    out = out.rename(columns=rename_map)
    for col in REQUIRED_OHLC + ['Volume']:
        if col not in out.columns:
            if col == 'Volume':
                out[col] = 0.0
            else:
                out[col] = pd.NA
        out[col] = pd.to_numeric(out[col], errors='coerce')
    return out


def write_history(market: str, symbol: str, df: pd.DataFrame) -> Path:
    out = normalize_ohlcv(df)
    p = history_path(market, symbol)
    p.parent.mkdir(parents=True, exist_ok=True)
    if out.index.name is None:
        out.index.name = 'Date'
    out.reset_index().to_csv(p, index=False, compression='gzip')
    return p


def last_bar(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or df.empty:
        return {}
    row = df.iloc[-1]
    return {
        'date': str(pd.Timestamp(df.index[-1]).date()),
        'close': float(row.get('Close')) if pd.notna(row.get('Close')) else None,
        'volume': float(row.get('Volume')) if pd.notna(row.get('Volume')) else None,
    }
