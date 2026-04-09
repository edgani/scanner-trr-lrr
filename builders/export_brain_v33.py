from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from scanner_vfinal.scanner.brain import export_brain, resolve_macro_file, resolve_macro_root, scanner_brain_file


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', help='Macro snapshot file or macro root directory')
    ap.add_argument('--macro-root', help='Extracted MacroRegime v33 root folder (contains .cache/latest_snapshot.json)')
    ap.add_argument('--target', help='Output scanner brain json path')
    args = ap.parse_args()

    if args.macro_root:
        os.environ['SCANNER_MACRO_ROOT'] = args.macro_root
    source = Path(args.source) if args.source else resolve_macro_file()
    target = Path(args.target) if args.target else scanner_brain_file()
    payload = export_brain(source_file=source, target_file=target)
    print(json.dumps({
        'generated_at': payload.get('generated_at'),
        'source_macro_root': str(resolve_macro_root()),
        'source_snapshot_file': payload.get('source_snapshot_file'),
        'current_quad': payload.get('current_quad'),
        'structural_quad': payload.get('structural_quad'),
        'monthly_quad': payload.get('monthly_quad'),
        'next_quad': payload.get('next_quad'),
        'current_route': payload.get('current_route'),
        'next_route': payload.get('next_route'),
        'alt_route': payload.get('alt_route'),
        'safe_harbor': payload.get('safe_harbor'),
        'best_beneficiary': payload.get('best_beneficiary'),
    }, indent=2))
