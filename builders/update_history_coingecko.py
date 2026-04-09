from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from scanner_vfinal.scanner.history import existing_history_state, write_history
from scanner_vfinal.scanner.registry import load_universe
from scanner_vfinal.scanner.sanity import evaluate_history_sanity

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIR = ROOT / 'data' / 'scans'
JOB_DIR = SCAN_DIR / 'jobs'
MARKET_URL = 'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart'


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _download(coin_id: str, session: requests.Session | None = None) -> pd.DataFrame | None:
    sess = session or requests.Session()
    resp = sess.get(
        MARKET_URL.format(coin_id=coin_id),
        params={'vs_currency': 'usd', 'days': 'max', 'interval': 'daily'},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    prices = data.get('prices', [])
    vols = data.get('total_volumes', [])
    if not prices:
        return None
    close_df = pd.DataFrame(prices, columns=['ts', 'Close'])
    vol_df = pd.DataFrame(vols, columns=['ts', 'Volume']) if vols else pd.DataFrame(columns=['ts', 'Volume'])
    close_df['Date'] = pd.to_datetime(close_df['ts'], unit='ms', utc=True).dt.tz_convert(None).dt.normalize()
    if not vol_df.empty:
        vol_df['Date'] = pd.to_datetime(vol_df['ts'], unit='ms', utc=True).dt.tz_convert(None).dt.normalize()
        close_df = close_df.merge(vol_df[['Date', 'Volume']], on='Date', how='left')
    close_df = close_df.drop_duplicates(subset=['Date']).sort_values('Date')
    close_df['Open'] = close_df['Close'].shift(1).fillna(close_df['Close'])
    close_df['High'] = close_df[['Open', 'Close']].max(axis=1)
    close_df['Low'] = close_df[['Open', 'Close']].min(axis=1)
    return close_df.set_index('Date')[['Open', 'High', 'Low', 'Close', 'Volume']]


def _select_rows(offset: int, limit: int | None, refresh_mode: str) -> list[dict[str, str]]:
    uni = load_universe('crypto')
    rows = uni.to_dict(orient='records')
    if limit is not None:
        rows = rows[offset: offset + limit]
    else:
        rows = rows[offset:]
    if refresh_mode == 'all':
        return rows
    selected: list[dict[str, str]] = []
    for row in rows:
        symbol = str(row['symbol'])
        state = existing_history_state('crypto', symbol)
        if refresh_mode == 'missing' and state.exists:
            continue
        if refresh_mode == 'stale' and state.exists and state.ok:
            continue
        selected.append(row)
    return selected


def _write_job_state(payload: dict[str, Any]) -> None:
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    (JOB_DIR / 'crypto_coingecko_job_state.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')


def build_market(
    offset: int = 0,
    limit: int | None = None,
    refresh_mode: str = 'stale',
    sleep_seconds: float = 1.35,
) -> dict[str, Any]:
    rows = _select_rows(offset=offset, limit=limit, refresh_mode=refresh_mode)
    attempted = len(rows)
    updated = 0
    processed = 0
    failed: list[str] = []
    sanity_rejected: list[str] = []
    session = requests.Session()
    session.headers.update({'accept': 'application/json', 'user-agent': 'scanner-vfinal/1.0'})

    for row in rows:
        symbol = str(row['symbol'])
        coin_id = str(row.get('coingecko_id') or symbol.split(':', 1)[-1]).strip()
        try:
            df = _download(coin_id, session=session)
            if df is None or df.empty:
                failed.append(symbol)
                processed += 1
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)
                continue
            write_history('crypto', symbol, df)
            sanity = evaluate_history_sanity('crypto', df)
            if not sanity.ok:
                sanity_rejected.append(symbol)
            updated += 1
            processed += 1
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
        except Exception:
            failed.append(symbol)
            processed += 1
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
        _write_job_state({
            'market': 'crypto',
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
        })

    report = {
        'market': 'crypto',
        'generated_at': _utc_now(),
        'refresh_mode': refresh_mode,
        'offset': offset,
        'limit': limit,
        'requested': attempted,
        'processed': processed,
        'updated': updated,
        'failed': failed,
        'sanity_rejected': sanity_rejected,
        'done': processed >= attempted,
        'next_offset_hint': None if limit is None else offset + limit,
    }
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    (SCAN_DIR / 'crypto_history_refresh_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--offset', type=int, default=0)
    ap.add_argument('--limit', type=int)
    ap.add_argument('--refresh-mode', choices=['missing', 'stale', 'all'], default='stale')
    ap.add_argument('--sleep-seconds', type=float, default=1.35)
    args = ap.parse_args()
    print(json.dumps(build_market(
        offset=args.offset,
        limit=args.limit,
        refresh_mode=args.refresh_mode,
        sleep_seconds=args.sleep_seconds,
    ), indent=2))
