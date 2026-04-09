from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.components.regime_ribbon import render_regime_ribbon
from ui.components.macro_impact_board import render_macro_impact_board
from ui.components.checklist_panel import render_checklist_panel
from ui.components.event_bubble_panel import render_event_bubble_panel
from ui.components.next_macro_panel import render_next_macro_panel
from ui.components.rotation_flow_panel import render_rotation_flow_panel
from ui.components.rotation_flow_logic import build_dashboard_global_flows
from ui.components.compact_table_helpers import frame_height
from ui.components.master_rotation_graph import render_master_rotation_graph
from utils.streamlit_utils import info_card


def _dashboard_flows(snapshot: dict) -> list[dict]:
    shared = snapshot['shared_core']
    rotation = shared.get('rotation', {})
    next_macro = shared.get('next_macro_summary', {})
    next_path = shared.get('next_path', {}) or {}
    best = str(rotation.get('best_beneficiary', 'XAUUSD'))
    safe = str(rotation.get('safe_harbor', 'USD'))
    return [{
        'label': 'Resolved Rotation Now',
        'summary': f"Execution now mengacu ke operating regime {shared.get('resolved_regime', {}).get('operating_regime', '-')}.",
        'tone': 'blue',
        'steps': [
            {'title': best, 'rank': 'best', 'note': rotation.get('best_beneficiary_why', ''), 'tickers': [best], 'tone': 'good'},
            {'title': safe, 'rank': 'safe harbor', 'note': rotation.get('safe_harbor_why', ''), 'tickers': [safe], 'tone': 'warn'},
            {'title': 'Next macro', 'rank': 'catalyst', 'note': next_macro.get('headline', '-'), 'tickers': [str(next_macro.get('family', 'macro')).upper()], 'tone': 'blue'},
            {'title': 'Next regime', 'rank': 'if-then', 'note': next_path.get('next_resolved_regime', '-'), 'tickers': [next_path.get('next_structural_quad', '-'), next_path.get('next_monthly_quad', '-')], 'tone': 'bad'},
        ],
    }]


def _forward_lines(shared: dict) -> list[str]:
    nxt = shared.get('next_path', {}) or {}
    struct_cands = ', '.join(f"{x.get('quad')} {100*float(x.get('prob',0.0)):.0f}%" for x in (nxt.get('structural_candidates', []) or [])[:2]) or '-'
    month_cands = ', '.join(f"{x.get('quad')} {100*float(x.get('prob',0.0)):.0f}%" for x in (nxt.get('monthly_candidates', []) or [])[:2]) or '-'
    return [
        f"Next structural: {nxt.get('next_structural_quad', '-')}",
        f"Struct cands: {struct_cands}",
        f"Next monthly: {nxt.get('next_monthly_quad', '-')}",
        f"Month cands: {month_cands}",
        f"Next operating: {nxt.get('next_resolved_regime', '-')}",
        f"Flip hazard: {100*float(nxt.get('flip_hazard', 0.0)):.0f}%",
    ]


def _breadth_lines(shared: dict) -> list[str]:
    snap = shared.get('breadth_snapshot', {}) or {}
    return [
        f"State: {snap.get('breadth_state', '-')}",
        f"Trend: {snap.get('breadth_trend', '-')}",
        f"Score: {float(snap.get('breadth_score', 0.0) or 0.0):.2f}",
        f"Sector support: {float(snap.get('sector_support_ratio', 0.0) or 0.0):.2f}",
        f"Narrow leadership: {float(snap.get('narrow_leadership', 0.0) or 0.0):.2f}",
    ]


def render_dashboard_main_page(snapshot: dict) -> None:
    st.title('Dashboard Utama')
    shared = snapshot['shared_core']
    dashboard = snapshot['dashboard']

    render_regime_ribbon(shared)
    render_master_rotation_graph(snapshot.get('master_graph', {}), title='Master Correlated Rotation Mind Map')

    a, b, c = st.columns([1.0, 0.9, 0.9], gap='small')
    with a:
        render_macro_impact_board(dashboard['macro_impact_global'], show_lists=False, show_catalyst=False)
        render_rotation_flow_panel(_dashboard_flows(snapshot), title='Resolved Rotation')
    with b:
        mg = snapshot.get('master_graph', {}) or {}
        info_card('Current Stage / Active Path', [f"Stage: {mg.get('current_stage', '-')}", f"Path: {mg.get('active_path', '-')}", f"Next watch: {mg.get('next_branch_watch', '-')}"], accent='#365b46')
        info_card('Forward-Looking Regime', _forward_lines(shared), accent='#5d4b3b')
        info_card('Breadth / Leadership Health', _breadth_lines(shared), accent='#365b46')
    with c:
        render_next_macro_panel(dashboard.get('next_macro', [])[:3], dashboard.get('next_macro_summary', {}), title='Next Macro', columns=1)
        render_checklist_panel(dashboard.get('global_checklist', [])[:5], title='Global Checklist')
        info_card('Top Risks', dashboard.get('top_risks', [])[:4], accent='#633535')
        info_card('Top Drivers Now', dashboard.get('top_drivers', [])[:4], accent='#365b46')

    low_left, low_mid, low_right = st.columns(3, gap='small')
    flows = build_dashboard_global_flows(snapshot)
    with low_left:
        render_rotation_flow_panel(flows[:1], title='Long Bias')
    with low_mid:
        render_rotation_flow_panel(flows[1:2], title='Short / Hedge')
    with low_right:
        render_rotation_flow_panel(flows[2:3], title='Escape / Safe Harbor')

    render_event_bubble_panel(dashboard.get('event_bubble', [])[:4])

    t1, t2 = st.columns(2, gap='small')
    with t1:
        st.subheader('Strongest vs Weakest Market')
        rows = dashboard.get('strongest_markets', [])
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True, height=frame_height(len(df), base=56, row=26, max_height=150))
    with t2:
        st.subheader('Quick Transmission Map')
        qt = dashboard.get('quick_transmission', {})
        df_qt = pd.DataFrame([{'route': k, 'note': v} for k, v in qt.items()])
        st.dataframe(df_qt, use_container_width=True, hide_index=True, height=frame_height(len(df_qt), base=56, row=26, max_height=150))

    with st.expander('Open setup preview', expanded=False):
        preview = dashboard.get('setup_preview', [])
        if preview:
            df_prev = pd.DataFrame(preview)
            keep = [c for c in ['market', 'name', 'side', 'action', 'score'] if c in df_prev.columns]
            st.dataframe(df_prev[keep], use_container_width=True, hide_index=True, height=frame_height(len(df_prev), base=72, row=30, max_height=240))
        else:
            st.info('Belum ada preview setup yang siap ditampilkan.')

        cats = dashboard.get('catalyst_overlays', {}) or {}
        if cats:
            rows = []
            for market, cat in cats.items():
                rows.append({
                    'market': market.upper(),
                    'theme': cat.get('title', '-'),
                    'state': cat.get('state', '-'),
                    'beneficiaries': ', '.join(cat.get('beneficiaries', [])[:3]),
                })
            st.markdown('**Catalyst / Theme Overlay**')
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=frame_height(len(rows), base=72, row=30, max_height=220))

        cov = dashboard.get('coverage_reports', {}) or {}
        if cov:
            rows = []
            for market, rep in cov.items():
                rows.append({
                    'market': market.upper(),
                    'ranking': int(rep.get('ranking_universe_size', 0) or 0),
                    'bucket': int(rep.get('bucket_universe_size', 0) or 0),
                    'backend': int(rep.get('backend_universe_size', 0) or 0),
                    'unbucketed': len(rep.get('unbucketed_symbols', []) or []),
                })
            st.markdown('**Routing Coverage Snapshot**')
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=frame_height(len(rows), base=72, row=30, max_height=220))
