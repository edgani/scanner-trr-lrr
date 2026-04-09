from __future__ import annotations

import streamlit as st


def render_score_explain_panel(title: str, score: float, notes: list[str] | None = None) -> None:
    st.subheader(title)
    st.write(f"Score: {score:.2f}")
    for note in notes or []:
        st.write(f"- {note}")
