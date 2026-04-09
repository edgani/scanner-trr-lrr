from __future__ import annotations
from pathlib import Path
import pandas as pd
from config.settings import HISTORY_DIR

_REQUIRED = ['Open','High','Low','Close','Volume']

def _safe_symbol(symbol: str) -> str:
    return symbol.replace('/', '_').replace('=', '_').replace('^', '_').replace('-', '_').replace('.', '_')

def _legacy_symbol(symbol: str) -> str:
    return symbol.replace('/', '_').replace('=', '_').replace('^', '_').replace('-', '_')

def history_path(market: str, symbol: str) -> Path:
    path = HISTORY_DIR / market
    path.mkdir(parents=True, exist_ok=True)
    return path / f'{_safe_symbol(symbol)}.csv.gz'

def _candidate_paths(market: str, symbol: str) -> list[Path]:
    base = HISTORY_DIR / market
    base.mkdir(parents=True, exist_ok=True)
    return [
        base / f'{_safe_symbol(symbol)}.csv.gz',
        base / f'{_legacy_symbol(symbol)}.csv.gz',
        base / f'{symbol}.csv.gz',
    ]

def load_history(market: str, symbol: str) -> pd.DataFrame | None:
    for path in _candidate_paths(market, symbol):
        if not path.exists():
            continue
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        cols = [c for c in _REQUIRED if c in df.columns]
        if len(cols) < 4 or df.empty:
            continue
        df = df[cols].sort_index()
        return df
    return None

def merge_histories(old: pd.DataFrame | None, new: pd.DataFrame | None) -> pd.DataFrame | None:
    if new is None or new.empty:
        return old
    new = new.sort_index()
    if old is None or old.empty:
        return new
    both = pd.concat([old, new]).sort_index()
    both = both[~both.index.duplicated(keep='last')]
    both = both.dropna(subset=['Close'])
    return both

def save_history(market: str, symbol: str, df: pd.DataFrame) -> Path:
    path = history_path(market, symbol)
    df = df.sort_index()
    df.to_csv(path, compression='gzip')
    return path

def history_status(market: str, symbols: list[str]) -> dict:
    present = 0
    missing = 0
    for symbol in symbols:
        if load_history(market, symbol) is not None:
            present += 1
        else:
            missing += 1
    return {'present': present, 'missing': missing, 'requested': len(symbols)}
