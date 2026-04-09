from __future__ import annotations

import streamlit as st

from ui.components.opportunity_table import render_opportunity_table
from utils.streamlit_utils import metric_card


def render_opportunity_board_page(snapshot: dict) -> None:
    st.title('Opportunity Board')
    board = snapshot.get('master_opportunities', {}) or {}
    life = snapshot.get('position_lifecycle', {}) or {}
    rows = board.get('rows', []) or []

    top = st.columns(4, gap='small')
    with top[0]: metric_card('Total rows', str(len(rows)), 'master ranked opportunities')
    with top[1]: metric_card('Actionable', str(sum(1 for r in rows if r.get('state') == 'Actionable')), 'live setups')
    with top[2]: metric_card('Watchlist', str(sum(1 for r in rows if r.get('state') != 'Actionable')), 'next opportunities')
    with top[3]: metric_card('Reviews due', str(len(life.get('due_reviews', []) or [])), 'countdown expiries')

    filters = st.columns(4, gap='small')
    with filters[0]:
        market = st.selectbox('Market filter', ['All', 'US', 'IHSG', 'FX', 'Commodities', 'Crypto'], index=0)
    with filters[1]:
        horizon = st.selectbox('Horizon filter', ['All', 'Trade', 'Trend', 'Tail'], index=0)
    with filters[2]:
        state = st.selectbox('State filter', ['All', 'Actionable', 'Watchlist'], index=0)
    with filters[3]:
        micro = st.selectbox('Microstructure filter', ['All', 'Flagged only', 'Clean only'], index=0)

    filtered = rows
    if market != 'All':
        filtered = [r for r in filtered if r.get('market') == market]
    if horizon != 'All':
        filtered = [r for r in filtered if r.get('horizon') == horizon]
    if state != 'All':
        filtered = [r for r in filtered if r.get('state') == state]
    if micro == 'Flagged only':
        filtered = [r for r in filtered if str(r.get('microstructure_flag', '') or '').strip()]
    elif micro == 'Clean only':
        filtered = [r for r in filtered if not str(r.get('microstructure_flag', '') or '').strip()]

    ihsg_flagged = sum(1 for r in rows if r.get('market') == 'IHSG' and str(r.get('microstructure_flag', '') or '').strip())
    st.caption(f"IHSG flagged rows: {ihsg_flagged} · filter ini cuma nambah konteks, bukan auto-buang ticker.")

    render_opportunity_table(filtered, 'Master ranked opportunities', cols=['ticker','market','bias','horizon','entry_zone','invalidation','target','countdown_days_left','review_state','next_action','macro_aligned','route_source_label','confidence','ev_score','microstructure_flag'])
