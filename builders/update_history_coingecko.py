from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from scanner_vfinal.scanner.history import write_history
from scanner_vfinal.scanner.registry import load_universe
from scanner_vfinal.scanner.sanity import evaluate_history_sanity

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIR = ROOT / 'data' / 'scans'
MARKET_URL = 'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart'


def _download(coin_id: str) -> pd.DataFrame | None:
    resp = requests.get(MARKET_URL.format(coin_id=coin_id), params={'vs_currency': 'usd', 'days': 'max', 'interval': 'daily'}, timeout=60)
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


def build_market(limit: int | None = None, sleep_seconds: float = 1.3) -> dict[str, Any]:
    uni = load_universe('crypto')
    if limit:
        uni = uni.head(limit)
    updated = 0
    failed: list[str] = []
    sanity_rejected: list[str] = []
    for _, row in uni.iterrows():
        symbol = str(row['symbol'])
        coin_id = str(row.get('coingecko_id') or symbol.split(':', 1)[-1]).strip()
        try:
            df = _download(coin_id)
            if df is None or df.empty:
                failed.append(symbol)
                continue
            write_history('crypto', symbol, df)
            sanity = evaluate_history_sanity('crypto', df)
            if not sanity.ok:
                sanity_rejected.append(symbol)
            updated += 1
            time.sleep(sleep_seconds)
        except Exception:
            failed.append(symbol)
    report = {
        'market': 'crypto',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'requested': int(len(uni)),
        'updated': updated,
        'failed': failed,
        'sanity_rejected': sanity_rejected,
    }
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    (SCAN_DIR / 'crypto_history_refresh_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int)
    ap.add_argument('--sleep-seconds', type=float, default=1.3)
    args = ap.parse_args()
    print(json.dumps(build_market(args.limit, args.sleep_seconds), indent=2))
