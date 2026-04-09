from __future__ import annotations

from typing import Any, Dict, Iterable

from data.event_loader import load_event_library, load_macro_calendar
from data.fred_loader import load_fred_bundle
from data.news_loader import load_news_signals
from data.price_loader import load_price_bundle


def load_all_data(
    tickers: Iterable[str],
    period: str = 'max',
    *,
    force_refresh: bool = False,
    prefer_local_history: bool = True,
) -> Dict[str, Any]:
    fred_bundle = load_fred_bundle(force_refresh=force_refresh)
    price_bundle = load_price_bundle(
        tickers,
        period=period,
        force_refresh=force_refresh,
        prefer_local_history=prefer_local_history,
    )

    fred_series = fred_bundle['series']
    price_series = price_bundle['series']
    loader_meta = {
        'fred': fred_bundle.get('meta', {}),
        'prices': price_bundle.get('meta', {}),
    }
    loader_meta['overall'] = {
        'real_share': 0.50 * float(loader_meta['fred'].get('real_share', 0.0)) + 0.50 * float(loader_meta['prices'].get('real_share', 0.0)),
        'fred_real_share': float(loader_meta['fred'].get('real_share', 0.0)),
        'price_real_share': float(loader_meta['prices'].get('real_share', 0.0)),
    }

    return {
        'fred': fred_series,
        'prices': price_series,
        'events': load_event_library(),
        'macro_calendar': load_macro_calendar(force_refresh=force_refresh),
        'news': load_news_signals(force_refresh=force_refresh),
        'loader_meta': loader_meta,
    }
