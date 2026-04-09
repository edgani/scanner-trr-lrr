from __future__ import annotations

from config.display_names import DISPLAY_NAME_MAP


def to_display(symbol: str) -> str:
    sx = str(symbol).strip()
    if sx in DISPLAY_NAME_MAP:
        return DISPLAY_NAME_MAP[sx]
    if sx.upper().startswith('CG:'):
        return sx.split(':', 1)[1]
    return sx
