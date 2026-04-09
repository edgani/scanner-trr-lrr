from __future__ import annotations
import streamlit as st
from utils.streamlit_utils import info_card


def _collect(section: dict, keys: list[str]) -> list[str]:
    out = []
    seen = set()
    for key in keys:
        for item in section.get(key, []) or []:
            sx = str(item).strip()
            if sx and sx not in seen:
                out.append(sx)
                seen.add(sx)
    return out


def render_strong_weak_map(section: dict) -> None:
    st.subheader('Strong vs Weak')
    # Prioritize actual tradable names/pairs/tokens first, then thematic buckets.
    strong = _collect(section, ['strong_names','strong_pairs','strong_tokens','strong_currencies','strong_sectors','strong_families'])
    weak = _collect(section, ['weak_names','weak_pairs','weak_tokens','weak_currencies','weak_sectors','weak_families'])
    c1, c2 = st.columns(2, gap='small')
    with c1:
        info_card('Strong', strong[:8], accent='#246b5a')
    with c2:
        info_card('Weak', weak[:8], accent='#6b2c2c')
