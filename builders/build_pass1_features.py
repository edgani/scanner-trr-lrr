from __future__ import annotations

import json
from pathlib import Path

from scanner_vfinal.scanner.brain import load_brain
from scanner_vfinal.scanner.history import load_history
from scanner_vfinal.scanner.pass1 import evaluate_one, results_to_frame
from scanner_vfinal.scanner.registry import load_universe

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIR = ROOT / 'data' / 'scans'


def tradable_hint(bucket: str) -> bool:
    return bucket not in {'junk_structure'}


if __name__ == '__main__':
    brain = load_brain()
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    for market in ['us', 'ihsg', 'forex', 'commodities', 'crypto']:
        uni = load_universe(market)
        policy = ((brain.get('market_brains', {}) or {}).get(market) or {}).copy()
        results = []
        for _, row in uni.iterrows():
            symbol = str(row['symbol'])
            hist = load_history(market, symbol)
            if hist is not None:
                hist.attrs['symbol'] = symbol
            res = evaluate_one(
                market=market,
                bucket=str(row['bucket']),
                df=hist,
                policy=policy,
                tradable_hint=tradable_hint(str(row['bucket'])),
            )
            results.append(res)
        out = results_to_frame(results)
        out.to_csv(SCAN_DIR / f'{market}_pass1.csv', index=False)
        print(json.dumps({'market': market, 'rows': len(out), 'kept': int((out['reject_reason'] == '').sum()) if not out.empty else 0}, indent=2))
