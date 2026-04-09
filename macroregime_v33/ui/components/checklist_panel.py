from __future__ import annotations
import streamlit as st
from utils.streamlit_utils import render_pills

def render_checklist_panel(items: list[dict], title: str = 'Checklist') -> None:
    st.subheader(title)
    pills=[(f"{row.get('label')} · {row.get('state')}", row.get('tone','neutral')) for row in items]
    render_pills(pills)
