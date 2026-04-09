from __future__ import annotations

from ui.components.market_page_layout import render_market_page


def render_forex_page(snapshot: dict) -> None:
    render_market_page(
        title='Forex',
        section=snapshot['fx'],
        checklist_title='Forex Checklist',
        hub_title='Currency / Pair Hubs',
        master_graph=snapshot.get('master_graph', {}),
        market_key='fx',
    )
