from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.components.compact_table_helpers import frame_height
from utils.streamlit_utils import info_card
from ui.components.master_rotation_graph import render_master_rotation_graph


def render_cross_asset_page(snapshot: dict) -> None:
    st.title('Cross-Asset')
    sec = snapshot.get('cross_asset', {})
    regime = snapshot.get('shared_core', {}).get('regime_stack', {}) or {}
    resolved = regime.get('resolved', {}) or {}
    next_path = snapshot.get('shared_core', {}).get('next_path', {}) or {}
    em_rotation = sec.get('em_rotation', {}) or {}
    petrodollar = sec.get('petrodollar', {}) or {}

    c1, c2, c3, c4 = st.columns(4, gap='small')
    c1.metric('Structural', regime.get('structural', {}).get('quad', '-'))
    c2.metric('Monthly', regime.get('monthly', {}).get('quad', '-'))
    c3.metric('Operating', resolved.get('resolved_language', resolved.get('operating_regime', '-')))
    c4.metric('Dominant', f"{resolved.get('dominant_horizon', '-')} · {resolved.get('confidence_band', '-')}")

    render_master_rotation_graph(snapshot.get('master_graph', {}), title='Cross-Asset Master View')

    rows = []
    for market, data in sec.get('global_chain_map', {}).items():
        rows.append({
            'market': market,
            'structural': ' | '.join(data.get('structural_paths', [])[:1]),
            'monthly': ' | '.join(data.get('monthly_paths', [])[:1]),
            'resolved': ' | '.join(data.get('resolved_paths', [])[:1]),
            'next': data.get('next_route', '-'),
        })
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True, height=frame_height(len(df), base=70, row=28, max_height=220))

    rotation = sec.get('rotation', {}) or {}
    aligned_assets = ', '.join((rotation.get('resolved_rotation', {}) or {}).get('leaders', [])) or '-'
    divergent_assets = ', '.join((rotation.get('monthly_rotation', {}) or {}).get('leaders', [])) or '-'
    safe_harbors = ', '.join((rotation.get('resolved_rotation', {}) or {}).get('safe_harbors', [])) or ', '.join((rotation.get('structural_rotation', {}) or {}).get('leaders', [])[:2]) or '-'
    next_broadening = ', '.join((rotation.get('next_rotation', {}) or {}).get('leaders', [])) or '-'
    next_breakdown = ', '.join((rotation.get('resolved_rotation', {}) or {}).get('laggards', [])[:3]) or '-'
    b1, b2, b3, b4 = st.columns(4, gap='small')
    with b1:
        mg = snapshot.get('master_graph', {}) or {}
        info_card('Conflict / Confirm', [
            f"Current stage: {mg.get('current_stage', '-')}",
            f"Active path: {mg.get('active_path', '-')}",
            f"Next resolved: {next_path.get('next_resolved_regime', '-')}",
            f"Conflicts: {len(sec.get('conflict_map', {}) or {})}",
            f"Confirms: {len(sec.get('confirmation_map', {}) or {})}",
        ], accent='#3a4b66')
    with b2:
        mg = snapshot.get('master_graph', {}) or {}
        info_card('Rotation / Safe Harbor', [
            f"Aligned: {aligned_assets}",
            f"Divergent: {divergent_assets}",
            f"Safe harbors: {safe_harbors}",
            f"Active names: {', '.join((mg.get('resolved', {}) or {}).get('tickers', [])[:3]) or '-'}",
            f"Next watch: {', '.join((mg.get('next', {}) or {}).get('tickers', [])[:3]) or '-'}",
        ], accent='#4d425f')
    with b3:
        info_card('EM Rotation', [
            f"Structural: {em_rotation.get('structural_state', '-')}",
            f"Monthly: {em_rotation.get('monthly_state', '-')}",
            f"Resolved: {em_rotation.get('resolved_state', '-')}",
            f"Next: {em_rotation.get('next_route', '-')}",
        ], accent='#365b46')
    with b4:
        info_card('Petrodollar', [
            f"State: {petrodollar.get('state', 'normal')} ({petrodollar.get('score', 0.0):.2f})",
            f"Importer pain: {petrodollar.get('em_importer_pain', 0.0):.2f}",
            f"Next: {petrodollar.get('next_route', '-')}",
        ], accent='#5b4a3d')
