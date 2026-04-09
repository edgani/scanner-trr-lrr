from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scanner.engine import build_market_snapshot
from config.settings import MARKET_ORDER

def main() -> None:
    for market in MARKET_ORDER:
        df, manifest = build_market_snapshot(market, force_refresh=False, use_cached_only=True)
        print(f"{market}: rows={len(df)} eligible={manifest.get('eligible')} coverage={manifest.get('coverage')}%")

if __name__ == '__main__':
    main()
