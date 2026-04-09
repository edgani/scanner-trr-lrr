from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from scanner_vfinal.config.display_names import display_symbol
from scanner_vfinal.scanner.brain import load_brain
from scanner_vfinal.scanner.history import load_history
from scanner_vfinal.scanner.manifests import write_manifest
from scanner_vfinal.scanner.pass2 import build_rows
from scanner_vfinal.scanner.ranking import rank
from scanner_vfinal.scanner.registry import load_universe
from scanner_vfinal.scanner.sanity import evaluate_history_sanity

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIR = ROOT / 'data' / 'scans'


def build_market(market: str, brain: dict) -> dict:
    uni = load_universe(market)
    pass1_file = SCAN_DIR / f'{market}_pass1.csv'
    p1 = pd.read_csv(pass1_file) if pass1_file.exists() else pd.DataFrame()
    p1_by_symbol = {str(r['symbol']): dict(r) for _, r in p1.iterrows()} if not p1.empty else {}
    rows = []
    history_loaded = 0
    sanity_rejected = 0
    eligible_count = 0
    for _, row in uni.iterrows():
        symbol = str(row['symbol'])
        hist = load_history(market, symbol)
        if hist is None or hist.empty:
            continue
        history_loaded += 1
        sanity = evaluate_history_sanity(market, hist)
        if not sanity.ok:
            sanity_rejected += 1
            continue
        p1_row = p1_by_symbol.get(symbol)
        if not p1_row:
            continue
        if str(p1_row.get('reject_reason', '')):
            continue
        if float(p1_row.get('pass1_score', 0.0) or 0.0) < 0.45:
            continue
        eligible_count += 1
        rows.extend(build_rows(market, symbol, display_symbol(symbol), str(row['bucket']), p1_row, hist, brain))
    out = pd.DataFrame(rows)
    if not out.empty:
        out = rank(out)
        out.to_csv(SCAN_DIR / f'{market}_scanner_snapshot.csv', index=False)
    else:
        pd.DataFrame(columns=['market','symbol','display_symbol','bucket','horizon_bucket','long_or_short','bias','entry_zone','invalidation','target','holding_window','macro_aligned','rr_score','ev_score','route','macro_explanation','why_now','why_not_yet','as_of']).to_csv(SCAN_DIR / f'{market}_scanner_snapshot.csv', index=False)
    manifest = {
        'market': market,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'snapshot_status': 'ready' if history_loaded > 0 else 'empty',
        'status_reason': '' if history_loaded > 0 else 'No built history yet.',
        'universe_count': int(len(uni)),
        'history_loaded': int(history_loaded),
        'eligible_count': int(eligible_count),
        'rows_count': int(len(out)),
        'sanity_rejected_count': int(sanity_rejected),
        'current_quad': brain.get('current_quad'),
        'next_quad': brain.get('next_quad'),
        'current_route': brain.get('current_route'),
        'next_route': brain.get('next_route'),
        'invalidator_route': brain.get('invalidator_route'),
        'execution_mode': (brain.get('execution_mode', {}) or {}).get('label') or (brain.get('execution_mode', {}) or {}).get('mode'),
        'market_health': brain.get('market_health'),
        'shock_state': brain.get('shock_state'),
        'crash_state': brain.get('crash_state'),
        'safe_harbor': brain.get('safe_harbor'),
        'best_beneficiary': brain.get('best_beneficiary'),
        'note': 'Locally built snapshot only. Page load never fetches live prices.',
    }
    write_manifest(market, manifest)
    return manifest


if __name__ == '__main__':
    brain = load_brain()
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    for market in ['us', 'ihsg', 'forex', 'commodities', 'crypto']:
        print(json.dumps(build_market(market, brain), indent=2))
