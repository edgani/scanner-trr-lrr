from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scanner.engine import build_market_snapshot
from config.settings import MARKET_ORDER

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--market', choices=MARKET_ORDER, required=True)
    parser.add_argument('--force-refresh', action='store_true')
    parser.add_argument('--use-cached-only', action='store_true')
    args = parser.parse_args()
    df, manifest = build_market_snapshot(args.market, force_refresh=args.force_refresh, use_cached_only=args.use_cached_only)
    print(f"{args.market}: rows={len(df)} eligible={manifest.get('eligible')} coverage={manifest.get('coverage')}%")

if __name__ == '__main__':
    main()
