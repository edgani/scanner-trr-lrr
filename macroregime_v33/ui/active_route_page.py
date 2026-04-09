from __future__ import annotations

import streamlit as st

from utils.streamlit_utils import metric_card, info_card, render_pills
from ui.components.opportunity_table import render_opportunity_table


def _render_path(path: dict, title: str) -> None:
    if not path:
        return
    st.subheader(title)
    st.caption(str(path.get('summary', '-')))
    cols = st.columns(max(1, len(path.get('nodes', []) or [])), gap='small')
    for idx, node in enumerate(path.get('nodes', []) or []):
        with cols[idx]:
            info_card(node.get('label', '-'), [
                f"Stage: {node.get('stage', '-')}",
                f"Dir: {node.get('direction', '-')}",
                f"Strength: {node.get('strength', '-')}",
                str(node.get('why', '-')),
                f"Tickers: {', '.join((node.get('attached_tickers') or [])[:4]) or '-'}",
            ], accent='#365b46' if not node.get('is_override') else '#7a5d12')
    edge_lines = [f"{e.get('causal_label','-')} ({e.get('polarity','-')})" for e in (path.get('edges', []) or [])]
    if edge_lines:
        info_card('Edges / why it connects', edge_lines[:8], accent='#28425f')
    c1, c2 = st.columns(2, gap='small')
    with c1:
        info_card('Confirmations', list(path.get('confirmations', [])[:5]) or ['-'], accent='#365b46')
    with c2:
        info_card('Invalidators', list(path.get('invalidators', [])[:5]) or ['-'], accent='#6a3340')


def render_active_route_page(snapshot: dict) -> None:
    st.title('Active Route')
    routes = snapshot.get('master_routes', {}) or {}
    active = routes.get('active_route', {}) or {}
    override = routes.get('override_route') or {}
    alternates = routes.get('alternate_routes', []) or []
    opp_rows = snapshot.get('master_opportunities', {}).get('rows', []) or []

    top = st.columns(4, gap='small')
    with top[0]: metric_card('Dominant family', str(routes.get('dominant_family', '-')).replace('_', ' '), 'route in control')
    with top[1]: metric_card('Active path conf', f"{float(active.get('confidence', 0.0) or 0.0):.2f}", 'path confidence')
    with top[2]: metric_card('EM rotation', str(routes.get('em_rotation_summary', '-')), 'branch status')
    with top[3]: metric_card('Petrodollar', str(routes.get('petrodollar_summary', '-')), 'transmission branch')

    render_pills([
        ('Active path', 'good'),
        ('Override' if override else 'No override', 'warn' if override else 'neutral'),
        (f"Alternates {len(alternates)}", 'blue'),
    ])

    _render_path(active, 'Base route')
    if override:
        _render_path(override, 'Override route')

    if alternates:
        alt = alternates[0]
        info_card('Alternate route to watch', [
            str(alt.get('summary', '-')),
            f"Confirm: {', '.join((alt.get('confirmations') or [])[:2]) or '-'}",
            f"Break: {', '.join((alt.get('invalidators') or [])[:2]) or '-'}",
        ], accent='#5d4b3b')

    active_id = active.get('path_id')
    related = [r for r in opp_rows if r.get('route_source_id') == active_id][:10]
    render_opportunity_table(related, 'Best expressions from active route', cols=['ticker','market','bias','horizon','countdown_days_left','review_state','next_action','confidence','ev_score'], empty_msg='Belum ada row yang terhubung ke route aktif.')
