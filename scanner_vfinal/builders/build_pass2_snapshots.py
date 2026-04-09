from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import re

import pandas as pd

from scanner_vfinal.config.display_names import display_symbol
from scanner_vfinal.scanner.registry import load_universe
from scanner_vfinal.scanner.brain import load_brain, next_route
from scanner_vfinal.scanner.pass2 import build_rows
from scanner_vfinal.scanner.ranking import rank
from scanner_vfinal.scanner.manifests import write_manifest

ROOT = Path(__file__).resolve().parents[1]
HISTORY_DIR = ROOT / 'data' / 'history'
SCAN_DIR = ROOT / 'data' / 'scans'


def safe_name(symbol: str) -> str:
    return re.sub(r'[^A-Za-z0-9._-]+', '_', symbol)


def load_history(market: str, symbol: str) -> pd.DataFrame | None:
    p = HISTORY_DIR / market / f"{safe_name(symbol)}.csv.gz"
    if not p.exists():
        return None
    df = pd.read_csv(p)
    date_col = 'Date' if 'Date' in df.columns else df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col)
    return df


def build_market(market: str, brain: dict) -> None:
    uni = load_universe(market)
    pass1_file = SCAN_DIR / f"{market}_pass1.csv"
    p1 = pd.read_csv(pass1_file) if pass1_file.exists() else pd.DataFrame()
    p1_by_symbol = {str(r['symbol']): dict(r) for _, r in p1.iterrows()}
    rows = []
    hist_loaded = 0
    elig = 0
    nr = next_route(brain)
    for _, row in uni.iterrows():
        symbol = str(row['symbol'])
        pr = p1_by_symbol.get(symbol)
        if not pr:
            continue
        hist = load_history(market, symbol)
        if hist is not None and not hist.empty:
            hist_loaded += 1
        if pr.get('reject_reason'):
            continue
        if float(pr.get('pass1_score', 0.0)) < 0.45:
            continue
        elig += 1
        rows.extend(build_rows(market, symbol, display_symbol(symbol), str(row['bucket']), pr, hist, brain, nr))
    out = pd.DataFrame(rows)
    if not out.empty:
        out = rank(out)
        out.to_csv(SCAN_DIR / f"{market}_scanner_snapshot.csv", index=False)
    else:
        pd.DataFrame(columns=['market','symbol','display_symbol','bucket','horizon_bucket','long_or_short','bias','entry_zone','invalidation','target','holding_window','macro_aligned','rr_score','ev_score','route','macro_explanation','why_now','why_not_yet']).to_csv(SCAN_DIR / f"{market}_scanner_snapshot.csv", index=False)
    manifest = {
        'market': market,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'universe_count': int(len(uni)),
        'history_loaded': int(hist_loaded),
        'eligible_count': int(elig),
        'rows_count': int(len(out)),
        'current_quad': brain.get('current_quad'),
        'next_quad': brain.get('next_quad'),
    }
    write_manifest(market, manifest)
    print(json.dumps(manifest, indent=2))


def main() -> None:
    brain = load_brain()
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    for market in ['us', 'ihsg', 'forex', 'commodities', 'crypto']:
        build_market(market, brain)


if __name__ == '__main__':
    main()
