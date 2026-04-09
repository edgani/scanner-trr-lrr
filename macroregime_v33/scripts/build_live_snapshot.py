from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json

from orchestration.build_snapshot import build_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description='Build latest MacroRegime snapshot using local history plus live tail refresh.')
    parser.add_argument('--force-refresh', action='store_true', help='Refresh provider data before rebuilding snapshot.')
    parser.add_argument('--compact-mode', action='store_true', help='Enable compact-mode build.')
    args = parser.parse_args()

    snap = build_snapshot(force_refresh=args.force_refresh, prefer_saved=False, compact_mode=args.compact_mode)
    print(json.dumps({
        'generated_at': snap.get('meta', {}).get('generated_at'),
        'schema': snap.get('meta', {}).get('schema'),
        'runtime_mode': snap.get('meta', {}).get('runtime_mode'),
        'prices_loaded': snap.get('meta', {}).get('loader_meta', {}).get('prices', {}).get('loaded'),
        'history_present': snap.get('meta', {}).get('history_meta', {}).get('present'),
    }, indent=2))


if __name__ == '__main__':
    main()
