from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.components.compact_table_helpers import frame_height


def render_market_structure_panel(section: dict, title: str = 'Market Hubs / Structure') -> None:
    st.subheader(title)
    if not section:
        st.info('Belum ada market structure.')
        return

    scalar_rows = []
    complex_rows = {}
    for k, v in section.items():
        if isinstance(v, (int, float, str, bool)) or v is None:
            scalar_rows.append({'metric': k, 'value': v})
        else:
            complex_rows[k] = v

    if scalar_rows:
        df = pd.DataFrame(scalar_rows)
        st.dataframe(df, use_container_width=True, hide_index=True, height=frame_height(len(df), base=72, row=34, max_height=260))

    for key, value in complex_rows.items():
        st.markdown(f"**{key}**")
        if isinstance(value, dict):
            rows = []
            for kk, vv in value.items():
                rows.append({'item': kk, 'value': vv if not isinstance(vv, list) else ' | '.join(map(str, vv[:10]))})
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True, height=frame_height(len(df), base=72, row=34, max_height=240))
        elif isinstance(value, list):
            st.caption(' · '.join(map(str, value[:10])))
        else:
            st.caption(value)
