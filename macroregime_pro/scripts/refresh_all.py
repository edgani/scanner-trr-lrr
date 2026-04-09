from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.universe_loader import get_backend_universe
from data.price_loader import load_price_bundle
from orchestration.build_snapshot import build_snapshot
from config.settings import DEFAULT_PRICE_PERIOD


def main() -> None:
    universe = get_backend_universe()
    symbols: list[str] = []
    for market in ('us', 'ihsg', 'fx', 'commodities', 'crypto'):
        for sym in universe.get(market, []):
            if sym not in symbols:
                symbols.append(sym)
    meta = load_price_bundle(symbols, period=DEFAULT_PRICE_PERIOD, force_refresh=True, prefer_local_history=True).get('meta', {})
    snap = build_snapshot(force_refresh=False, prefer_saved=False, compact_mode=True)
    print({
        'history_requested': meta.get('requested'),
        'history_loaded': meta.get('loaded'),
        'snapshot_generated_at': snap.get('meta', {}).get('generated_at'),
    })


if __name__ == '__main__':
    main()
