from __future__ import annotations

from typing import Dict, Iterable

import numpy as np
import pandas as pd

from config.settings import (
    DEFAULT_PRICE_PERIOD,
    DEFAULT_REFRESH_PERIOD,
    LIVE_FETCH_ENABLED,
    PRICE_CACHE_TTL_SECONDS,
    PRICE_FULL_BOOTSTRAP_PERIOD,
    PRICE_INCREMENTAL_REFRESH_PERIOD,
    PRICE_UPDATE_BATCH_SIZE,
)
from data.history_store import history_coverage, load_history, merge_history, save_history
from utils.streamlit_compat import st

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None


def _safe_series(obj, symbol: str | None = None) -> pd.Series:
    if obj is None:
        return pd.Series(dtype=float, name=symbol)
    if isinstance(obj, pd.Series):
        ser = pd.to_numeric(obj, errors="coerce").dropna()
    elif isinstance(obj, pd.DataFrame):
        if "Close" in obj.columns:
            ser = pd.to_numeric(obj["Close"], errors="coerce").dropna()
        else:
            nums = obj.select_dtypes(include=[np.number])
            ser = pd.to_numeric(nums.iloc[:, 0], errors="coerce").dropna() if not nums.empty else pd.Series(dtype=float)
    else:
        ser = pd.Series(dtype=float)
    if not ser.empty:
        idx = pd.to_datetime(ser.index, errors='coerce')
        if getattr(idx, 'tz', None) is not None:
            idx = idx.tz_convert('UTC').tz_localize(None)
        ser.index = idx
        ser = ser[~ser.index.isna()].sort_index()
        ser = ser[~ser.index.duplicated(keep='last')]
    ser.name = symbol or getattr(ser, 'name', None)
    return ser


def _empty_meta(requested: tuple[str, ...]) -> dict:
    return {
        'requested': len(requested),
        'loaded': 0,
        'missing': len(requested),
        'loaded_keys': [],
        'missing_keys': list(requested),
        'real_share': 0.0,
        'provider': 'yfinance',
        'history_store_hits': 0,
        'history_store_misses': len(requested),
        'history_mode': 'empty',
        'fetched_from_provider': 0,
    }


def _extract_to_out(data, batch: list[str], out: Dict[str, pd.Series]) -> None:
    if data is None or getattr(data, 'empty', True):
        return
    multi = isinstance(getattr(data, 'columns', None), pd.MultiIndex)
    for t in batch:
        try:
            if multi:
                if (t, 'Close') in data.columns:
                    out[t] = _safe_series(data[(t, 'Close')], t)
                elif t in data.columns.get_level_values(0):
                    sub = data[t]
                    if 'Close' in sub.columns:
                        out[t] = _safe_series(sub['Close'], t)
            elif 'Close' in data.columns and len(batch) == 1:
                out[t] = _safe_series(data['Close'], t)
        except Exception:
            out[t] = pd.Series(dtype=float, name=t)


def _provider_download(batch: list[str], period: str) -> Dict[str, pd.Series]:
    out: Dict[str, pd.Series] = {t: pd.Series(dtype=float, name=t) for t in batch}
    if yf is None or not batch:
        return out
    try:
        data = yf.download(
            batch,
            period=period,
            auto_adjust=True,
            progress=False,
            group_by='ticker',
            threads=False,
            timeout=8,
        )
        _extract_to_out(data, batch, out)
    except Exception:
        for t in batch:
            try:
                data = yf.download(
                    t,
                    period=period,
                    auto_adjust=True,
                    progress=False,
                    group_by='ticker',
                    threads=False,
                    timeout=6,
                )
                _extract_to_out(data, [t], out)
            except Exception:
                out[t] = pd.Series(dtype=float, name=t)
    return out


def _load_local_histories(requested: tuple[str, ...]) -> Dict[str, pd.Series]:
    return {t: load_history(t) for t in requested}


def _refresh_symbols(requested: tuple[str, ...], existing: Dict[str, pd.Series], force_refresh: bool) -> tuple[Dict[str, pd.Series], int]:
    if not LIVE_FETCH_ENABLED or yf is None or not requested:
        return existing, 0
    to_fetch: list[str] = []
    if not force_refresh:
        return existing, 0
    for t in requested:
        ser = existing.get(t, pd.Series(dtype=float))
        if force_refresh or ser.empty:
            to_fetch.append(t)
    fetched = 0
    if not to_fetch:
        return existing, fetched
    for i in range(0, len(to_fetch), PRICE_UPDATE_BATCH_SIZE):
        batch = to_fetch[i:i + PRICE_UPDATE_BATCH_SIZE]
        batch_period = PRICE_FULL_BOOTSTRAP_PERIOD if any(existing.get(t, pd.Series(dtype=float)).empty for t in batch) else PRICE_INCREMENTAL_REFRESH_PERIOD
        fresh = _provider_download(batch, period=batch_period)
        for t in batch:
            merged = merge_history(existing.get(t, pd.Series(dtype=float)), fresh.get(t, pd.Series(dtype=float)), symbol=t)
            if not merged.empty:
                save_history(t, merged)
                existing[t] = merged
                if not fresh.get(t, pd.Series(dtype=float)).empty:
                    fetched += 1
            else:
                existing.setdefault(t, pd.Series(dtype=float, name=t))
    return existing, fetched


@st.cache_data(ttl=PRICE_CACHE_TTL_SECONDS, show_spinner=False)
def load_price_bundle(
    tickers: Iterable[str],
    period: str = DEFAULT_PRICE_PERIOD,
    *,
    force_refresh: bool = False,
    prefer_local_history: bool = True,
) -> dict:
    requested = tuple(dict.fromkeys(str(t).strip() for t in tickers if str(t).strip()))
    out: Dict[str, pd.Series] = _load_local_histories(requested) if prefer_local_history else {t: pd.Series(dtype=float, name=t) for t in requested}
    meta = _empty_meta(requested)

    coverage = history_coverage(requested)
    out, fetched = _refresh_symbols(requested, out, force_refresh=force_refresh)

    if not force_refresh and not prefer_local_history and LIVE_FETCH_ENABLED and yf is not None:
        # backward-compatible direct live path
        direct = _provider_download(list(requested), period=period or DEFAULT_PRICE_PERIOD)
        for t in requested:
            merged = merge_history(out.get(t, pd.Series(dtype=float)), direct.get(t, pd.Series(dtype=float)), symbol=t)
            if not merged.empty:
                out[t] = merged
                save_history(t, merged)
                if not direct.get(t, pd.Series(dtype=float)).empty:
                    fetched += 1

    loaded_keys = [k for k, v in out.items() if not getattr(v, 'empty', True)]
    missing_keys = [k for k in requested if k not in loaded_keys]
    meta.update({
        'requested': len(requested),
        'loaded': len(loaded_keys),
        'missing': len(missing_keys),
        'loaded_keys': loaded_keys,
        'missing_keys': missing_keys,
        'real_share': (len(loaded_keys) / max(len(requested), 1)),
        'provider': 'yfinance',
        'history_store_hits': int(coverage.get('present', 0)),
        'history_store_misses': int(coverage.get('missing', 0)),
        'history_mode': 'local_history_plus_live_tail' if LIVE_FETCH_ENABLED else 'local_history_only',
        'fetched_from_provider': fetched,
        'requested_period': period,
        'stored_period_policy': DEFAULT_PRICE_PERIOD,
    })
    return {'series': out, 'meta': meta}


@st.cache_data(ttl=PRICE_CACHE_TTL_SECONDS, show_spinner=False)
def load_prices(
    tickers: Iterable[str],
    period: str = DEFAULT_PRICE_PERIOD,
    *,
    force_refresh: bool = False,
    prefer_local_history: bool = True,
) -> Dict[str, pd.Series]:
    return load_price_bundle(
        tickers,
        period=period,
        force_refresh=force_refresh,
        prefer_local_history=prefer_local_history,
    )['series']
