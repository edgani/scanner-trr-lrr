from __future__ import annotations
import streamlit as st
from utils.streamlit_utils import render_pills


def render_execution_map_panel(section: dict) -> None:
    st.subheader('Execution Map')
    mode = section.get('mode', '-')
    score = float(section.get('score', 0.0))
    bias = section.get('bias', 'Long bias')
    good_modes = {'Long Now','Short Now','Add on Reset','Long on Reset','Short on Bounce','Rates / importer pain pairs now','Tactical exporter / resource long on reset','Long/short clean divergences now'}
    warn_modes = {'Wait Reclaim','Wait Reset','Wait Long Reclaim','Wait Short Reclaim','Tactical Only','Tactical Long','Tactical Short','Selective defensives / banks only','Dollar / funding stress expressions','Wait cleaner repricing','Defensive / selective only'}
    tone = 'good' if mode in good_modes else ('warn' if mode in warn_modes else 'bad')
    render_pills([(str(bias), 'blue'), (str(mode), tone), (f"Score {score:.2f}", 'blue')])
    for note in section.get('notes', []):
        st.write(f"- {note}")
