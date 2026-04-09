from __future__ import annotations

from ui.components.market_page_layout import render_market_page


def render_ihsg_page(snapshot: dict) -> None:
    render_market_page(
        title='IHSG',
        section=snapshot['ihsg'],
        checklist_title='IHSG Checklist',
        hub_title='Market Hubs IHSG',
        master_graph=snapshot.get('master_graph', {}),
        market_key='ihsg',
    )
