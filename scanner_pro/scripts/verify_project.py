from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scanner.snapshot_store import load_snapshot
from config.settings import MARKET_ORDER, SIMPLE_TABLE_COLUMNS


def main() -> None:
    required = set(SIMPLE_TABLE_COLUMNS)
    for market in MARKET_ORDER:
        df2, man2 = load_snapshot(market)
        if df2 is None:
            raise RuntimeError(f'No snapshot for {market}. Run build_everything_full.py first.')
        missing = required - set(df2.columns)
        if missing:
            raise RuntimeError(f'{market} missing columns: {missing}')
        print(f"OK {market}: rows={len(df2)} universe={man2.get('universe')} coverage={man2.get('coverage')}%")
    print('Scanner verify: snapshot files look usable.')


if __name__ == '__main__':
    main()
