from __future__ import annotations

import streamlit as st

from utils.streamlit_utils import info_card, metric_card


def render_scenario_lab_page(snapshot: dict) -> None:
    st.title('Scenario Lab')
    lab = snapshot.get('scenario_lab', {}) or {}
    top = st.columns(4, gap='small')
    with top[0]: metric_card('Active route', snapshot.get('master_routes', {}).get('dominant_family', '-'), 'dominant family')
    with top[1]: metric_card('Alt routes', str(len(lab.get('alternate_routes', []) or [])), 'future branches')
    with top[2]: metric_card('Next resolved', str(lab.get('next_resolved_regime', '-')), 'current next-path')
    with top[3]: metric_card('Switch triggers', str(len(lab.get('switch_triggers', []) or [])), 'if-then triggers')

    c1, c2 = st.columns(2, gap='small')
    with c1:
        info_card('Continuation path', [
            str(lab.get('continuation_path', '-')),
            f"Monthly fade: {lab.get('monthly_fade_path', '-')}",
            f"Structural flip: {lab.get('structural_flip_path', '-')}",
        ], accent='#365b46')
    with c2:
        info_card('What breaks the current route', list(lab.get('invalidators', [])[:5]) or ['-'], accent='#6a3340')

    alts = lab.get('alternate_routes', []) or []
    for alt in alts:
        info_card(str(alt.get('name', 'Alternate route')), [
            str(alt.get('summary', '-')),
            f"Confirm: {', '.join((alt.get('confirmations') or [])[:2]) or '-'}",
            f"Break: {', '.join((alt.get('invalidators') or [])[:2]) or '-'}",
        ], accent='#5d4b3b')

    impact = lab.get('scenario_tab_impact_map', []) or []
    if impact:
        rows = []
        for item in impact[:10]:
            rows.append({
                'Scenario': item.get('scenario', item.get('case', '-')),
                'Tab': item.get('tab', '-'),
                'Effect': item.get('impact', item.get('effect', '-')),
                'Why': item.get('why', item.get('summary', '-')),
            })
        st.subheader('Scenario -> market impact map')
        st.dataframe(rows, use_container_width=True, hide_index=True)
