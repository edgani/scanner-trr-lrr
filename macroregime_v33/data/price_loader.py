from __future__ import annotations

from typing import Dict, Iterable
import time

import numpy as np
import pandas as pd

from config.settings import (
    COINGECKO_API_BASE,
    COINGECKO_DEMO_API_KEY,
    COINGECKO_HISTORY_DAYS,
    DEFAULT_PRICE_PERIOD,
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

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


_PRICE_COLS = ["Open", "High", "Low", "Close", "Volume"]


def _normalize_index(obj: pd.Series | pd.DataFrame):
    idx = pd.to_datetime(obj.index, errors="coerce")
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    obj.index = idx
    obj = obj[~obj.index.isna()].sort_index()
    obj = obj[~obj.index.duplicated(keep="last")]
    return obj


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
        ser = _normalize_index(ser)
    ser.name = symbol or getattr(ser, "name", None)
    return ser


def _empty_frame(symbol: str | None = None) -> pd.DataFrame:
    frame = pd.DataFrame(columns=_PRICE_COLS)
    frame.attrs["symbol"] = symbol
    return frame


def _frame_from_series(ser: pd.Series, symbol: str | None = None) -> pd.DataFrame:
    ser = _safe_series(ser, symbol)
    if ser.empty:
        return _empty_frame(symbol)
    frame = pd.DataFrame(index=ser.index)
    frame["Close"] = ser.astype(float)
    frame["Open"] = frame["Close"]
    frame["High"] = frame["Close"]
    frame["Low"] = frame["Close"]
    frame["Volume"] = np.nan
    frame = frame[_PRICE_COLS]
    frame.attrs["symbol"] = symbol
    return frame


def _safe_frame(obj, symbol: str | None = None) -> pd.DataFrame:
    if obj is None:
        return _empty_frame(symbol)
    if isinstance(obj, pd.Series):
        return _frame_from_series(obj, symbol)
    if not isinstance(obj, pd.DataFrame):
        return _empty_frame(symbol)
    frame = obj.copy()
    if frame.empty:
        return _empty_frame(symbol)
    # flatten unusual column labels
    frame.columns = [str(c[-1] if isinstance(c, tuple) else c) for c in frame.columns]
    nums = frame.select_dtypes(include=[np.number]).copy()
    if nums.empty:
        return _empty_frame(symbol)
    nums = _normalize_index(nums)
    clean = pd.DataFrame(index=nums.index)
    if "Close" in nums.columns:
        clean["Close"] = pd.to_numeric(nums["Close"], errors="coerce")
    else:
        clean["Close"] = pd.to_numeric(nums.iloc[:, 0], errors="coerce")
    clean["Open"] = pd.to_numeric(nums.get("Open", clean["Close"]), errors="coerce")
    high_src = nums.get("High", pd.concat([clean["Open"], clean["Close"]], axis=1).max(axis=1))
    low_src = nums.get("Low", pd.concat([clean["Open"], clean["Close"]], axis=1).min(axis=1))
    clean["High"] = pd.to_numeric(high_src, errors="coerce")
    clean["Low"] = pd.to_numeric(low_src, errors="coerce")
    if "Volume" in nums.columns:
        clean["Volume"] = pd.to_numeric(nums["Volume"], errors="coerce")
    else:
        clean["Volume"] = np.nan
    clean = clean.dropna(subset=["Close"])
    if clean.empty:
        return _empty_frame(symbol)
    # keep OHLC logically consistent
    high_floor = pd.concat([clean["Open"], clean["Close"], clean["High"]], axis=1).max(axis=1)
    low_cap = pd.concat([clean["Open"], clean["Close"], clean["Low"]], axis=1).min(axis=1)
    clean["High"] = high_floor.astype(float)
    clean["Low"] = low_cap.astype(float)
    clean = clean[_PRICE_COLS]
    clean.attrs["symbol"] = symbol
    return clean


def _empty_meta(requested: tuple[str, ...]) -> dict:
    return {
        "requested": len(requested),
        "loaded": 0,
        "missing": len(requested),
        "loaded_keys": [],
        "missing_keys": list(requested),
        "real_share": 0.0,
        "provider": "yfinance",
        "history_store_hits": 0,
        "history_store_misses": len(requested),
        "history_mode": "empty",
        "fetched_from_provider": 0,
        "ohlcv_loaded": 0,
        "ohlcv_share": 0.0,
    }


def _extract_bundle_to_out(data, batch: list[str], out_series: Dict[str, pd.Series], out_frames: Dict[str, pd.DataFrame]) -> None:
    if data is None or getattr(data, "empty", True):
        return
    multi = isinstance(getattr(data, "columns", None), pd.MultiIndex)
    for ticker in batch:
        try:
            if multi:
                if ticker in data.columns.get_level_values(0):
                    sub = data[ticker]
                    frame = _safe_frame(sub, ticker)
                else:
                    frame = _empty_frame(ticker)
            elif len(batch) == 1:
                frame = _safe_frame(data, ticker)
            else:
                frame = _empty_frame(ticker)
        except Exception:
            frame = _empty_frame(ticker)
        out_frames[ticker] = frame
        out_series[ticker] = _safe_series(frame["Close"] if not frame.empty and "Close" in frame.columns else None, ticker)





def _is_coingecko_symbol(symbol: str) -> bool:
    sx = str(symbol).strip()
    return sx.upper().startswith('CG:')


def _coingecko_id(symbol: str) -> str:
    return str(symbol).strip().split(':', 1)[1].strip().lower() if ':' in str(symbol) else str(symbol).strip().lower()


def _coingecko_headers() -> dict[str, str]:
    headers = {'accept': 'application/json', 'user-agent': 'MacroRegimePro/0.30'}
    if COINGECKO_DEMO_API_KEY:
        headers['x-cg-demo-api-key'] = COINGECKO_DEMO_API_KEY
    return headers


def _coingecko_fetch_history(symbol: str, days: str | int | None = None) -> tuple[pd.Series, pd.DataFrame]:
    if requests is None:
        return pd.Series(dtype=float, name=symbol), _empty_frame(symbol)
    coin_id = _coingecko_id(symbol)
    use_days = days or COINGECKO_HISTORY_DAYS or 'max'
    url = f"{COINGECKO_API_BASE}/coins/{coin_id}/market_chart"
    params = {'vs_currency': 'usd', 'days': use_days, 'interval': 'daily'}
    try:
        resp = requests.get(url, params=params, headers=_coingecko_headers(), timeout=20)
        resp.raise_for_status()
        payload = resp.json() if resp.content else {}
    except Exception:
        return pd.Series(dtype=float, name=symbol), _empty_frame(symbol)

    prices = payload.get('prices') or []
    vols = payload.get('total_volumes') or []
    if not prices:
        return pd.Series(dtype=float, name=symbol), _empty_frame(symbol)

    idx = pd.to_datetime([row[0] for row in prices], unit='ms', utc=True).tz_convert('UTC').tz_localize(None)
    close = pd.Series([float(row[1]) for row in prices], index=idx, name=symbol)
    close = close[~close.index.duplicated(keep='last')].sort_index()
    frame = _frame_from_series(close, symbol)
    if vols:
        vmap = {}
        for row in vols:
            try:
                vmap[pd.to_datetime(row[0], unit='ms', utc=True).tz_convert('UTC').tz_localize(None)] = float(row[1])
            except Exception:
                continue
        if vmap:
            vol_ser = pd.Series(vmap).reindex(frame.index).fillna(method='ffill').fillna(0.0)
            frame['Volume'] = vol_ser.astype(float)
    return close.astype(float), frame

def _provider_download_bundle(batch: list[str], period: str) -> tuple[Dict[str, pd.Series], Dict[str, pd.DataFrame]]:
    out_series: Dict[str, pd.Series] = {t: pd.Series(dtype=float, name=t) for t in batch}
    out_frames: Dict[str, pd.DataFrame] = {t: _empty_frame(t) for t in batch}
    if not batch:
        return out_series, out_frames

    cg_batch = [t for t in batch if _is_coingecko_symbol(t)]
    yf_batch = [t for t in batch if not _is_coingecko_symbol(t)]

    if yf_batch and yf is not None:
        try:
            data = yf.download(
                yf_batch,
                period=period,
                auto_adjust=True,
                progress=False,
                group_by="ticker",
                threads=False,
                timeout=8,
            )
            _extract_bundle_to_out(data, yf_batch, out_series, out_frames)
        except Exception:
            for ticker in yf_batch:
                try:
                    data = yf.download(
                        ticker,
                        period=period,
                        auto_adjust=True,
                        progress=False,
                        group_by="ticker",
                        threads=False,
                        timeout=6,
                    )
                    _extract_bundle_to_out(data, [ticker], out_series, out_frames)
                except Exception:
                    out_series[ticker] = pd.Series(dtype=float, name=ticker)
                    out_frames[ticker] = _empty_frame(ticker)

    for ticker in cg_batch:
        ser, frame = _coingecko_fetch_history(ticker, days=period if period not in {None, '', 'max'} else COINGECKO_HISTORY_DAYS)
        out_series[ticker] = ser
        out_frames[ticker] = frame
        time.sleep(0.15)
    return out_series, out_frames


def _load_local_histories(requested: tuple[str, ...]) -> Dict[str, pd.Series]:
    return {t: load_history(t) for t in requested}


@st.cache_data(ttl=PRICE_CACHE_TTL_SECONDS, show_spinner=False)
def load_price_bundle(
    tickers: Iterable[str],
    period: str = DEFAULT_PRICE_PERIOD,
    *,
    force_refresh: bool = False,
    prefer_local_history: bool = True,
) -> dict:
    requested = tuple(dict.fromkeys(str(t).strip() for t in tickers if str(t).strip()))
    series: Dict[str, pd.Series] = _load_local_histories(requested) if prefer_local_history else {t: pd.Series(dtype=float, name=t) for t in requested}
    frames: Dict[str, pd.DataFrame] = {t: _frame_from_series(series.get(t, pd.Series(dtype=float)), t) for t in requested}
    meta = _empty_meta(requested)

    coverage = history_coverage(requested)
    fetched = 0

    if LIVE_FETCH_ENABLED and requested:
        should_fetch = force_refresh or (not prefer_local_history)
        if should_fetch:
            to_fetch = list(requested)
            for i in range(0, len(to_fetch), PRICE_UPDATE_BATCH_SIZE):
                batch = to_fetch[i:i + PRICE_UPDATE_BATCH_SIZE]
                batch_period = (
                    PRICE_FULL_BOOTSTRAP_PERIOD
                    if any(series.get(t, pd.Series(dtype=float)).empty for t in batch)
                    else PRICE_INCREMENTAL_REFRESH_PERIOD
                )
                if not force_refresh and not prefer_local_history:
                    batch_period = period or DEFAULT_PRICE_PERIOD
                fresh_series, fresh_frames = _provider_download_bundle(batch, period=batch_period)
                for ticker in batch:
                    merged = merge_history(series.get(ticker, pd.Series(dtype=float)), fresh_series.get(ticker, pd.Series(dtype=float)), symbol=ticker)
                    if not merged.empty:
                        save_history(ticker, merged)
                        series[ticker] = merged
                        fetched += 1 if not fresh_series.get(ticker, pd.Series(dtype=float)).empty else 0
                    else:
                        series.setdefault(ticker, pd.Series(dtype=float, name=ticker))
                    frame = fresh_frames.get(ticker, _empty_frame(ticker))
                    frames[ticker] = frame if not frame.empty else _frame_from_series(series.get(ticker, pd.Series(dtype=float)), ticker)

    loaded_keys = [k for k, v in series.items() if not getattr(v, "empty", True)]
    missing_keys = [k for k in requested if k not in loaded_keys]
    ohlcv_loaded = sum(1 for k in requested if not frames.get(k, _empty_frame(k)).empty)
    meta.update({
        "requested": len(requested),
        "loaded": len(loaded_keys),
        "missing": len(missing_keys),
        "loaded_keys": loaded_keys,
        "missing_keys": missing_keys,
        "real_share": (len(loaded_keys) / max(len(requested), 1)),
        "provider": "yfinance",
        "history_store_hits": int(coverage.get("present", 0)),
        "history_store_misses": int(coverage.get("missing", 0)),
        "history_mode": "local_history_plus_live_tail" if LIVE_FETCH_ENABLED else "local_history_only",
        "fetched_from_provider": fetched,
        "requested_period": period,
        "stored_period_policy": DEFAULT_PRICE_PERIOD,
        "ohlcv_loaded": ohlcv_loaded,
        "ohlcv_share": (ohlcv_loaded / max(len(requested), 1)),
    })
    return {"series": series, "frames": frames, "meta": meta}


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
    )["series"]


def load_price_frames(
    tickers: Iterable[str],
    period: str = DEFAULT_PRICE_PERIOD,
    *,
    force_refresh: bool = False,
    prefer_local_history: bool = True,
) -> Dict[str, pd.DataFrame]:
    return load_price_bundle(
        tickers,
        period=period,
        force_refresh=force_refresh,
        prefer_local_history=prefer_local_history,
    )["frames"]
