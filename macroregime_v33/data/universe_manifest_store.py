from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

from config.settings import CACHE_BASE_DIR, UNIVERSE_DIRNAME


_MANIFEST_FILES = {
    'us': 'us_full_universe.json',
    'ihsg': 'ihsg_full_universe.json',
    'crypto': 'crypto_full_universe.json',
    'fx': 'fx_full_universe.json',
    'commodities': 'commodities_full_universe.json',
}


def universe_root(base_dir: str | None = None) -> Path:
    base = Path(base_dir or CACHE_BASE_DIR)
    return base / UNIVERSE_DIRNAME


def manifest_path(market: str, base_dir: str | None = None) -> Path:
    key = str(market).strip().lower()
    filename = _MANIFEST_FILES.get(key, f'{key}_full_universe.json')
    return universe_root(base_dir) / filename


def load_universe_manifest(market: str, base_dir: str | None = None) -> dict[str, Any]:
    path = manifest_path(market, base_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_universe_manifest(market: str, payload: dict[str, Any], base_dir: str | None = None) -> Path:
    path = manifest_path(market, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = dict(payload or {})
    clean.setdefault('market', str(market).lower().strip())
    clean.setdefault('generated_at', datetime.now(timezone.utc).isoformat())
    path.write_text(json.dumps(clean, indent=2, ensure_ascii=False), encoding='utf-8')
    return path


def manifest_symbols(payload: dict[str, Any]) -> list[str]:
    symbols: list[str] = []
    for row in payload.get('records', []) or []:
        if isinstance(row, dict):
            sym = str(row.get('symbol', '')).strip()
            if sym and sym not in symbols:
                symbols.append(sym)
    for sym in payload.get('symbols', []) or []:
        sx = str(sym).strip()
        if sx and sx not in symbols:
            symbols.append(sx)
    return symbols


def manifest_summary(payload: dict[str, Any]) -> dict[str, Any]:
    symbols = manifest_symbols(payload)
    stats = dict(payload.get('stats', {}) or {})
    return {
        'market': payload.get('market'),
        'generated_at': payload.get('generated_at'),
        'count': len(symbols),
        'source': payload.get('source'),
        'stats': stats,
        'has_records': bool(payload.get('records')),
    }
