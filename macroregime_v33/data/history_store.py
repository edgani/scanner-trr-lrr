from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import hashlib
import json

import pandas as pd

from config.settings import CACHE_BASE_DIR, HISTORY_DIRNAME, HISTORY_META_FILENAME


def _root(base_dir: str | None = None) -> Path:
    base = Path(base_dir or CACHE_BASE_DIR)
    return base / HISTORY_DIRNAME


def _safe_name(symbol: str) -> str:
    raw = str(symbol).strip()
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    safe = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in raw)
    return f"{safe}__{digest}.csv.gz"


def history_path(symbol: str, base_dir: str | None = None) -> Path:
    return _root(base_dir) / _safe_name(symbol)


def manifest_path(base_dir: str | None = None) -> Path:
    return _root(base_dir) / HISTORY_META_FILENAME


def load_history(symbol: str, base_dir: str | None = None) -> pd.Series:
    path = history_path(symbol, base_dir)
    if not path.exists():
        return pd.Series(dtype=float)
    try:
        df = pd.read_csv(path, compression='gzip')
        if df.empty or 'date' not in df.columns or 'close' not in df.columns:
            return pd.Series(dtype=float)
        idx = pd.to_datetime(df['date'], errors='coerce', utc=True)
        ser = pd.Series(pd.to_numeric(df['close'], errors='coerce').values, index=idx, name=symbol).dropna()
        ser = ser[~ser.index.isna()].sort_index()
        if getattr(ser.index, 'tz', None) is not None:
            ser.index = ser.index.tz_convert('UTC').tz_localize(None)
        return ser[~ser.index.duplicated(keep='last')]
    except Exception:
        return pd.Series(dtype=float)


def save_history(symbol: str, series: pd.Series, base_dir: str | None = None) -> Path:
    clean = pd.to_numeric(series, errors='coerce').dropna()
    if clean.empty:
        return history_path(symbol, base_dir)
    clean = clean.sort_index()
    if getattr(clean.index, 'tz', None) is not None:
        clean.index = clean.index.tz_convert('UTC').tz_localize(None)
    clean = clean[~clean.index.duplicated(keep='last')]
    path = history_path(symbol, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame({'date': clean.index.astype('datetime64[ns]').astype(str), 'close': clean.astype(float).values})
    df.to_csv(path, index=False, compression='gzip')
    update_manifest(symbol, clean, base_dir=base_dir)
    return path


def merge_history(existing: pd.Series, new: pd.Series, symbol: str | None = None) -> pd.Series:
    old = pd.to_numeric(existing, errors='coerce').dropna() if existing is not None else pd.Series(dtype=float)
    fresh = pd.to_numeric(new, errors='coerce').dropna() if new is not None else pd.Series(dtype=float)
    if old.empty and fresh.empty:
        return pd.Series(dtype=float, name=symbol)
    merged = pd.concat([old, fresh])
    merged = merged[~merged.index.duplicated(keep='last')].sort_index()
    if symbol:
        merged.name = symbol
    return merged


def _read_manifest(base_dir: str | None = None) -> dict:
    path = manifest_path(base_dir)
    if not path.exists():
        return {'symbols': {}, 'updated_at': None}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {'symbols': {}, 'updated_at': None}


def update_manifest(symbol: str, series: pd.Series, base_dir: str | None = None) -> dict:
    manifest = _read_manifest(base_dir)
    clean = pd.to_numeric(series, errors='coerce').dropna().sort_index()
    ret_20d = None
    ret_63d = None
    vol_21d = None
    downside_vol_21d = None
    if len(clean) >= 22:
        base = float(clean.iloc[-21]) if float(clean.iloc[-21]) != 0 else 0.0
        if base:
            ret_20d = float(clean.iloc[-1] / base - 1.0)
        rets = clean.pct_change().dropna().tail(21)
        if not rets.empty:
            vol_21d = float(rets.std())
            dn = rets[rets < 0]
            downside_vol_21d = float(dn.std()) if not dn.empty else 0.0
    if len(clean) >= 64:
        base = float(clean.iloc[-64]) if float(clean.iloc[-64]) != 0 else 0.0
        if base:
            ret_63d = float(clean.iloc[-1] / base - 1.0)
    info = {
        'rows': int(len(clean)),
        'first_date': str(clean.index[0].date()) if len(clean) else None,
        'last_date': str(clean.index[-1].date()) if len(clean) else None,
        'last_close': float(clean.iloc[-1]) if len(clean) else None,
        'ret_20d': ret_20d,
        'ret_63d': ret_63d,
        'vol_21d': vol_21d,
        'downside_vol_21d': downside_vol_21d,
    }
    manifest.setdefault('symbols', {})[str(symbol)] = info
    manifest['updated_at'] = datetime.now(timezone.utc).isoformat()
    path = manifest_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


def read_manifest(base_dir: str | None = None) -> dict:
    return _read_manifest(base_dir)


def history_coverage(symbols: Iterable[str], base_dir: str | None = None) -> dict:
    requested = [str(s).strip() for s in symbols if str(s).strip()]
    manifest = _read_manifest(base_dir)
    store = manifest.get('symbols', {}) or {}
    present = [s for s in requested if s in store and int(store[s].get('rows', 0) or 0) > 0]
    missing = [s for s in requested if s not in present]
    rows = {s: int((store.get(s, {}) or {}).get('rows', 0) or 0) for s in requested}
    return {
        'requested': len(requested),
        'present': len(present),
        'missing': len(missing),
        'present_symbols': present,
        'missing_symbols': missing,
        'rows_by_symbol': rows,
        'updated_at': manifest.get('updated_at'),
    }
