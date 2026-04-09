from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from scanner_vfinal.scanner.history import write_history
from scanner_vfinal.scanner.registry import load_universe
from scanner_vfinal.scanner.sanity import evaluate_history_sanity

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIR = ROOT / 'data' / 'scans'


def _download(symbol: str) -> pd.DataFrame | None:
    df = yf.download(
        symbol,
        period='max',
        interval='1d',
        auto_adjust=False,
        actions=True,
        progress=False,
        threads=False,
        repair=True,
    )
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.rename_axis('Date').reset_index().set_index('Date')
    return df


def build_market(market: str, limit: int | None = None) -> dict[str, Any]:
    uni = load_universe(market)
    if limit:
        uni = uni.head(limit)
    updated = 0
    failed: list[str] = []
    sanity_rejected: list[str] = []
    for _, row in uni.iterrows():
        symbol = str(row['symbol'])
        try:
            df = _download(symbol)
            if df is None or df.empty:
                failed.append(symbol)
                continue
            write_history(market, symbol, df)
            sanity = evaluate_history_sanity(market, df)
            if not sanity.ok:
                sanity_rejected.append(symbol)
            updated += 1
        except Exception:
            failed.append(symbol)
    report = {
        'market': market,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'requested': int(len(uni)),
        'updated': updated,
        'failed': failed,
        'sanity_rejected': sanity_rejected,
    }
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    (SCAN_DIR / f'{market}_history_refresh_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--market', action='append', choices=['us', 'ihsg', 'forex', 'commodities'])
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()
    for market in args.market or ['us', 'ihsg', 'forex', 'commodities']:
        print(json.dumps(build_market(market, args.limit), indent=2))
