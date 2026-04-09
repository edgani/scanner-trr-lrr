from __future__ import annotations

from ui.components.market_page_layout import render_market_page


def render_us_stocks_page(snapshot: dict) -> None:
    render_market_page(
        title='US Stocks',
        section=snapshot['us'],
        checklist_title='US Stocks Checklist',
        hub_title='Market Hubs US',
        master_graph=snapshot.get('master_graph', {}),
        market_key='us',
    )
