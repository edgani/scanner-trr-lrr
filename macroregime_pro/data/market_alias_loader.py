from __future__ import annotations

from config.display_names import DISPLAY_NAME_MAP


def to_display_name(symbol: str) -> str:
    return DISPLAY_NAME_MAP.get(symbol, symbol)
