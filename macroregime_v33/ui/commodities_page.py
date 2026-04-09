from __future__ import annotations

from ui.components.market_page_layout import render_market_page


def render_commodities_page(snapshot: dict) -> None:
    render_market_page(
        title='Commodities',
        section=snapshot['commodities'],
        checklist_title='Commodities Checklist',
        hub_title='Commodity Family Hubs',
        master_graph=snapshot.get('master_graph', {}),
        market_key='commodities',
    )
