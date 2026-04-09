from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.components.next_macro_panel import render_next_macro_panel
from ui.components.compact_table_helpers import frame_height
from ui.components.rotation_flow_panel import render_rotation_flow_panel
from ui.components.master_rotation_graph import render_master_rotation_graph
from utils.streamlit_utils import info_card, metric_card


def _scenario_flows(sec: dict) -> list[dict]:
    fam = sec.get('scenario_family', []) or []
    top = fam[:3]
    if not top:
        return []
    flows = []
    structural = sec.get('structural_quad', '-')
    monthly = sec.get('monthly_quad', structural)
    operating = sec.get('operating_regime', '-')
    divergence = sec.get('divergence_state', '-')
    nxt = sec.get('next_path', {}) or {}
    for idx, item in enumerate(top, start=1):
        flows.append({
            'label': f'Priority {idx}: {item}',
            'summary': f'Start from structural {structural}, overlay monthly {monthly}, then check whether signal confirms the branch. Current operating regime: {operating}.',
            'tone': 'blue' if idx == 1 else 'warn',
            'steps': [
                {'title': f'Structural {structural}', 'note': 'backbone regime', 'tone': 'blue'},
                {'title': f'Monthly {monthly}', 'note': f'divergence: {divergence}', 'tone': 'good' if divergence == 'aligned' else 'warn'},
                {'title': item, 'note': 'base branch', 'tone': 'good' if idx == 1 else 'blue'},
                {'title': sec.get('next_macro_family', '-'), 'note': sec.get('next_macro_countdown', '-') , 'tone': 'warn'},
                {'title': 'Next regime', 'note': nxt.get('next_resolved_regime', '-'), 'tone': 'blue'},
                {'title': 'Invalidator', 'note': 'kalau market tidak ikut confirm', 'tone': 'bad'},
            ],
        })
    return flows


def render_scenarios_page(snapshot: dict) -> None:
    st.title('Scenarios & What If')
    sec = snapshot.get('scenarios', {})

    m1, m2, m3, m4, m5, m6 = st.columns(6, gap='small')
    with m1:
        metric_card('Dominant news', sec.get('dominant_news', 'Quiet'))
    with m2:
        metric_card('Shock state', sec.get('shock_state', '-'))
    with m3:
        metric_card('Structural quad', sec.get('structural_quad', sec.get('current_quad', '-')))
    with m4:
        metric_card('Monthly quad', sec.get('monthly_quad', '-'))
    with m5:
        metric_card('Operating regime', sec.get('operating_regime', '-'))
    with m6:
        metric_card('Next macro countdown', sec.get('next_macro_countdown', '-'))

    if sec.get('divergence_state'):
        st.caption(f"Divergence: {sec.get('divergence_state')} · Dominant horizon: {sec.get('dominant_horizon', '-')} · Petrodollar: {sec.get('petrodollar_state', 'normal')}")

    render_master_rotation_graph(sec.get('master_graph', {}), title='Scenario branches from master graph')

    top_left, top_right = st.columns([1.0, 1.0], gap='small')
    with top_left:
        render_rotation_flow_panel(_scenario_flows(sec), title='Scenario Priority Flow')
    with top_right:
        render_next_macro_panel(
            sec.get('next_macro', []),
            {
                'headline': 'Economic releases that can change the branch',
                'note': sec.get('dominant_news', 'Quiet'),
                'impact_path': 'Countdown dipakai supaya jelas kapan catalyst besar seperti CPI, NFP, PCE, GDP, FOMC, atau JOLTS bisa memaksa scenario berpindah cabang atau menyelaraskan monthly vs structural quad.',
                'countdown': sec.get('next_macro_countdown', '-'),
                'family': sec.get('next_macro_family', '-'),
            },
            title='Macro Catalyst + Countdown',
            columns=1,
        )
        info_card('Forward Branch Tree', [
            f"Next structural quad: {sec.get('next_path', {}).get('next_structural_quad', '-')}",
            f"Next monthly quad: {sec.get('next_path', {}).get('next_monthly_quad', '-')}",
            f"Next operating regime: {sec.get('next_path', {}).get('next_resolved_regime', '-')}",
            str(sec.get('next_path', {}).get('continuation_path', '-')),
            str(sec.get('next_path', {}).get('monthly_fade_path', '-')),
            str(sec.get('next_path', {}).get('structural_flip_path', '-')),
            f"Petrodollar route: {sec.get('next_path', {}).get('petrodollar_route', '-')}",
            f"EM next route: {sec.get('next_path', {}).get('em_next_route', '-')}",
        ], accent='#4a4d73')
        info_card('Top Catalysts Now', sec.get('top_catalysts', []), accent='#244463')
        analog_state = sec.get('historical_analog_state', {}) or {}
        if analog_state:
            top = analog_state.get('top', {}) or {}
            info_card('Historical Analog Consequence', [
                f"Top analog: {top.get('label', '-')}",
                f"Similarity: {100 * float(top.get('similarity', 0.0)):.0f}%",
                f"Next bias: {top.get('next_bias', '-')}",
                f"Expected duration: {top.get('expected_duration', '-')}",
                f"Confidence adj: {top.get('confidence_adjustment', 0.0):+.2f}",
            ], accent='#5b4a3d')

    matrix = sec.get('what_if_matrix', {}) or {}
    if matrix:
        rows = []
        for name, data in matrix.items():
            rows.append({
                'scenario': name,
                'probability': round(100 * float(data.get('p', 0.0)), 1),
                'summary': data.get('desc', '-'),
                'winners': ' | '.join((data.get('winners') or [])[:3]),
                'losers': ' | '.join((data.get('losers') or [])[:3]),
                'invalidators': ' | '.join((data.get('invalidators') or [])[:2]),
            })
        df = pd.DataFrame(rows).sort_values('probability', ascending=False)
        st.subheader('What-If Matrix')
        st.dataframe(df, use_container_width=True, hide_index=True, height=frame_height(len(df), base=76, row=34, max_height=360))

    impact_map = sec.get('scenario_tab_impact_map', []) or []
    if impact_map:
        st.subheader('Scenario-to-Tab Impact Map')
        df = pd.DataFrame(impact_map)
        st.dataframe(df, use_container_width=True, hide_index=True, height=frame_height(len(df), base=76, row=34, max_height=320))

    bottom_left, bottom_right = st.columns(2, gap='small')
    with bottom_left:
        if sec.get('playbooks'):
            st.subheader('Policy Playbooks')
            df = pd.DataFrame(sec['playbooks'])
            st.dataframe(df, use_container_width=True, hide_index=True, height=frame_height(len(df), base=76, row=34, max_height=280))
    with bottom_right:
        if sec.get('analogs'):
            st.subheader('Historical Analogs')
            df = pd.DataFrame(sec['analogs'])
            st.dataframe(df, use_container_width=True, hide_index=True, height=frame_height(len(df), base=76, row=34, max_height=280))
