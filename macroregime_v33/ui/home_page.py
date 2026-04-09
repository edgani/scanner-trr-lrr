from __future__ import annotations

import streamlit as st

from ui.components.opportunity_table import render_opportunity_table
from utils.streamlit_utils import metric_card, info_card, render_pills


def _opp_label(row: dict | None) -> str:
    if not row:
        return '-'
    return f"{row.get('ticker','-')} · {row.get('bias','-')} · {row.get('horizon','-')}"


def render_home_page(snapshot: dict) -> None:
    st.title('Home')
    home = snapshot.get('home_summary', {}) or {}
    routes = snapshot.get('master_routes', {}) or {}
    opps = snapshot.get('master_opportunities', {}) or {}
    rows = opps.get('rows', []) or []

    top = st.columns(5, gap='small')
    with top[0]:
        metric_card('Dominant family', str(home.get('dominant_family', '-')).replace('_', ' '), 'route in control')
    with top[1]:
        metric_card('Best long', _opp_label(home.get('best_long')), 'highest EV+ long now')
    with top[2]:
        metric_card('Best short', _opp_label(home.get('best_short')), 'highest EV+ short now')
    with top[3]:
        metric_card('Best hedge', _opp_label(home.get('best_hedge')), 'best defensive expression')
    with top[4]:
        metric_card('Reviews due', str(home.get('due_reviews', 0)), 'countdown expiries to review')

    render_pills([
        (f"Route {routes.get('dominant_family', '-')}", 'blue'),
        (f"EM {routes.get('em_rotation_summary', '-')}", 'neutral'),
        (f"Petro {routes.get('petrodollar_summary', '-')}", 'warn'),
    ])

    c1, c2 = st.columns([1.15, 0.85], gap='small')
    with c1:
        info_card('Current dominant route', [
            str(routes.get('dominant_summary', '-')),
            f"Main invalidator: {home.get('main_risk', '-')}",
            f"Next catalyst: {home.get('next_catalyst', '-')} · {home.get('next_catalyst_countdown', '-')}",
        ], accent='#365b46')
    with c2:
        info_card('What to watch now', [
            f"Best long: {_opp_label(home.get('best_long'))}",
            f"Best short: {_opp_label(home.get('best_short'))}",
            f"Safe harbor / hedge: {_opp_label(home.get('safe_harbor'))}",
        ], accent='#5d4b3b')

    top_now_ids = set(opps.get('top_global_now', []) or [])
    top_now = [r for r in rows if r.get('opportunity_id') in top_now_ids]
    top_next_ids = set(opps.get('top_global_next', []) or [])
    top_next = [r for r in rows if r.get('opportunity_id') in top_next_ids]

    a, b = st.columns(2, gap='small')
    with a:
        render_opportunity_table(top_now[:8], 'Top opportunities now', cols=['ticker','market','bias','horizon','countdown_days_left','review_state','next_action','route_source_label','ev_score'])
    with b:
        render_opportunity_table(top_next[:8], 'Next opportunities', cols=['ticker','market','bias','horizon','countdown_days_left','review_state','next_action','route_source_label','ev_score'], empty_msg='Belum ada next opportunities yang menonjol.')
