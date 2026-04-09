from __future__ import annotations

from ui.components.market_page_layout import render_market_page


def render_crypto_page(snapshot: dict) -> None:
    render_market_page(
        title='Crypto',
        section=snapshot['crypto'],
        checklist_title='Crypto Checklist',
        hub_title='Market Hubs Crypto',
        master_graph=snapshot.get('master_graph', {}),
        market_key='crypto',
    )
