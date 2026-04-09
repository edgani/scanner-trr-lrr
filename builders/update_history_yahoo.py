from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from scanner_vfinal.scanner.history import existing_history_state, write_history
from scanner_vfinal.scanner.registry import load_universe
from scanner_vfinal.scanner.sanity import evaluate_history_sanity

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIR = ROOT / 'data' / 'scans'
JOB_DIR = SCAN_DIR / 'jobs'
YAHOO_MARKETS = ['us', 'ihsg', 'forex', 'commodities']


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_download(df: pd.DataFrame | None) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    if 'Date' not in df.columns:
        df = df.rename_axis('Date').reset_index()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date']).set_index('Date').sort_index()
    keep = [c for c in ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'] if c in df.columns]
    df = df[keep]
    return df if not df.empty else None


def _single_download(symbol: str) -> pd.DataFrame | None:
    raw = yf.download(
        symbol,
        period='max',
        interval='1d',
        auto_adjust=False,
        actions=True,
        progress=False,
        threads=False,
        repair=True,
        group_by='column',
    )
    return _normalize_download(raw)


def _batch_download(symbols: list[str]) -> dict[str, pd.DataFrame | None]:
    if not symbols:
        return {}
    if len(symbols) == 1:
        return {symbols[0]: _single_download(symbols[0])}
    raw = yf.download(
        symbols,
        period='max',
        interval='1d',
        auto_adjust=False,
        actions=True,
        progress=False,
        threads=False,
        repair=True,
        group_by='ticker',
    )
    out: dict[str, pd.DataFrame | None] = {s: None for s in symbols}
    if raw is None or raw.empty:
        return out
    if not isinstance(raw.columns, pd.MultiIndex):
        out[symbols[0]] = _normalize_download(raw)
        return out
    for symbol in symbols:
        try:
            sub = raw[symbol].copy()
        except Exception:
            sub = None
        out[symbol] = _normalize_download(sub)
    return out


def _select_symbols(market: str, offset: int, limit: int | None, refresh_mode: str) -> list[str]:
    uni = load_universe(market)
    symbols = [str(x) for x in uni['symbol'].tolist()]
    if limit is not None:
        symbols = symbols[offset: offset + limit]
    else:
        symbols = symbols[offset:]
    if refresh_mode == 'all':
        return symbols
    selected: list[str] = []
    for symbol in symbols:
        state = existing_history_state(market, symbol)
        if refresh_mode == 'missing' and state.exists:
            continue
        if refresh_mode == 'stale' and state.exists and state.ok:
            continue
        selected.append(symbol)
    return selected


def _write_job_state(market: str, payload: dict[str, Any]) -> None:
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    (JOB_DIR / f'{market}_yahoo_job_state.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')


def build_market(
    market: str,
    offset: int = 0,
    limit: int | None = None,
    batch_size: int = 25,
    refresh_mode: str = 'stale',
    fallback_single: bool = True,
    sleep_seconds: float = 0.2,
) -> dict[str, Any]:
    requested_symbols = _select_symbols(market, offset=offset, limit=limit, refresh_mode=refresh_mode)
    attempted = len(requested_symbols)
    processed = 0
    updated = 0
    failed: list[str] = []
    sanity_rejected: list[str] = []
    skipped_existing = 0

    for i in range(0, len(requested_symbols), max(batch_size, 1)):
        batch = requested_symbols[i:i + max(batch_size, 1)]
        batch_map = _batch_download(batch)
        batch_failures: list[str] = []
        for symbol in batch:
            df = batch_map.get(symbol)
            if df is None or df.empty:
                batch_failures.append(symbol)
                continue
            write_history(market, symbol, df)
            sanity = evaluate_history_sanity(market, df)
            if not sanity.ok:
                sanity_rejected.append(symbol)
            updated += 1
            processed += 1
        if fallback_single and batch_failures:
            for symbol in batch_failures:
                try:
                    df = _single_download(symbol)
                    if df is None or df.empty:
                        failed.append(symbol)
                        processed += 1
                        continue
                    write_history(market, symbol, df)
                    sanity = evaluate_history_sanity(market, df)
                    if not sanity.ok:
                        sanity_rejected.append(symbol)
                    updated += 1
                    processed += 1
                    if sleep_seconds > 0:
                        time.sleep(sleep_seconds)
                except Exception:
                    failed.append(symbol)
                    processed += 1
        state_payload = {
            'market': market,
            'generated_at': _utc_now(),
            'refresh_mode': refresh_mode,
            'offset': offset,
            'limit': limit,
            'attempted': attempted,
            'processed': processed,
            'updated': updated,
            'failed_count': len(failed),
            'sanity_rejected_count': len(sanity_rejected),
            'done': processed >= attempted,
            'next_offset_hint': None if limit is None else offset + limit,
        }
        _write_job_state(market, state_payload)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    report = {
        'market': market,
        'generated_at': _utc_now(),
        'refresh_mode': refresh_mode,
        'offset': offset,
        'limit': limit,
        'batch_size': batch_size,
        'requested': attempted,
        'processed': processed,
        'updated': updated,
        'skipped_existing': skipped_existing,
        'failed': failed,
        'sanity_rejected': sanity_rejected,
        'done': processed >= attempted,
        'next_offset_hint': None if limit is None else offset + limit,
    }
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    (SCAN_DIR / f'{market}_history_refresh_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--market', action='append', choices=YAHOO_MARKETS)
    ap.add_argument('--offset', type=int, default=0)
    ap.add_argument('--limit', type=int)
    ap.add_argument('--batch-size', type=int, default=25)
    ap.add_argument('--refresh-mode', choices=['missing', 'stale', 'all'], default='stale')
    ap.add_argument('--sleep-seconds', type=float, default=0.2)
    ap.add_argument('--no-fallback-single', action='store_true')
    args = ap.parse_args()
    for market in args.market or YAHOO_MARKETS:
        print(json.dumps(build_market(
            market=market,
            offset=args.offset,
            limit=args.limit,
            batch_size=args.batch_size,
            refresh_mode=args.refresh_mode,
            fallback_single=not args.no_fallback_single,
            sleep_seconds=args.sleep_seconds,
        ), indent=2))
