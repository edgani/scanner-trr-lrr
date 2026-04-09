from __future__ import annotations

import streamlit as st

from utils.streamlit_utils import render_pills


def render_macro_impact_board(section: dict, show_lists: bool = False, show_catalyst: bool = False) -> None:
    st.subheader('Macro vs Market')

    conf = float(section.get('confidence', 0.0))
    pills = [(f"Confidence {100*conf:.0f}%", 'blue')]
    if section.get('quad_tag'):
        pills.append((str(section.get('quad_tag')), 'warn'))
    render_pills(pills)

    st.markdown(f"**Sekarang:** {section.get('now','-')}")
    st.markdown(f"**Best path sekarang:** {section.get('best_expression','-')}")
    st.markdown(f"**Kalau leader mulai luntur:** {section.get('forward_branch','-')}")
    st.markdown(f"**Invalidator:** {section.get('invalidator','-')}")
    if section.get('breadth_state') or section.get('breadth_score') is not None:
        st.markdown(f"**Breadth:** {section.get('breadth_state','-')} · score {float(section.get('breadth_score', 0.0) or 0.0):.2f} · narrow {float(section.get('narrow_leadership', 0.0) or 0.0):.2f}")
