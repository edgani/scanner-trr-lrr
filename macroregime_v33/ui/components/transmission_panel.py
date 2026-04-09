from __future__ import annotations
import streamlit as st
from utils.streamlit_utils import info_card, render_pills


def render_transmission_panel(section: dict) -> None:
    st.subheader('Transmission / Spillover')
    structural = str(section.get('structural_quad', '-'))
    monthly = str(section.get('monthly_quad', structural))
    dominant = str(section.get('dominant_horizon', '-'))
    resolved_em = str(section.get('resolved_em_rotation', '-'))
    petrodollar = str(section.get('petrodollar_state', 'normal'))
    render_pills([(f"S {structural}", 'blue'), (f"M {monthly}", 'warn' if monthly != structural else 'good'), (f"{dominant}", 'blue'), (f"EM {resolved_em}", 'neutral'), (f"Petro {petrodollar}", 'warn' if petrodollar != 'normal' else 'good')])
    c1, c2 = st.columns(2, gap='small')
    with c1:
        info_card('Structural', section.get('structural_paths', section.get('paths', []))[:4], accent='#28425f')
        info_card('Monthly', section.get('monthly_paths', [section.get('monthly_trigger', '-')])[:4], accent='#35506e')
    with c2:
        info_card('Resolved', section.get('resolved_paths', [])[:4], accent='#3a4b66')
        lines = [*section.get('confirm', [])[:2], *[f"Conflict: {x}" for x in section.get('conflict', [])[:2]], f"Next: {section.get('next_route', '-')}"]
        info_card('Confirm / Conflict', lines, accent='#4d425f')
