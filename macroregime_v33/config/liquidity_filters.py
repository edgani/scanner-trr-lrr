from __future__ import annotations

from utils.series_utils import safe_series

MIN_BARS_BY_MARKET = {
    "us": 60,
    "ihsg": 60,
    "fx": 60,
    "commodities": 60,
    "crypto": 60,
}


def has_min_bars(series, market: str) -> bool:
    return len(safe_series(series)) >= MIN_BARS_BY_MARKET.get(market, 60)
