from __future__ import annotations

from pathlib import Path
import re
import pandas as pd

from scanner_vfinal.scanner.registry import load_universe
from scanner_vfinal.scanner.brain import load_brain, bucket_policy
from scanner_vfinal.scanner.pass1 import evaluate_one, results_to_frame

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
    df.attrs['symbol'] = symbol
    return df


def main() -> None:
    brain = load_brain()
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    for market in ['us', 'ihsg', 'forex', 'commodities', 'crypto']:
        uni = load_universe(market)
        policy = bucket_policy(brain, market)
        results = []
        for _, row in uni.iterrows():
            hist = load_history(market, str(row['symbol']))
            p1 = evaluate_one(market, str(row['bucket']), hist, policy)
            results.append(p1)
        out = results_to_frame(results)
        out.to_csv(SCAN_DIR / f"{market}_pass1.csv", index=False)
        print(f"pass1 {market}: {len(out)}")


if __name__ == '__main__':
    main()
