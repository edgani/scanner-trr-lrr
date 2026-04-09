from __future__ import annotations

import json

from scanner_vfinal.scanner.brain import export_brain


if __name__ == '__main__':
    payload = export_brain()
    print(json.dumps({
        'generated_at': payload.get('generated_at'),
        'current_quad': payload.get('current_quad'),
        'next_quad': payload.get('next_quad'),
        'safe_harbor': payload.get('safe_harbor'),
        'best_beneficiary': payload.get('best_beneficiary'),
    }, indent=2))
