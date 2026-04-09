from __future__ import annotations
import pandas as pd, streamlit as st
from ui.components.compact_table_helpers import frame_height


def _prep(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows).copy()
    if df.empty:
        return df
    if 'score' in df.columns:
        df['score'] = pd.to_numeric(df['score'], errors='coerce').fillna(0.0)
        df['edge'] = df['score'].abs()
    else:
        df['edge'] = 0.0
    return df


def _show(df: pd.DataFrame, title: str) -> None:
    if df.empty:
        return
    keep = [c for c in ['name','bucket','side','score','why_radar','not_ready','trigger','risk','radar_type'] if c in df.columns]
    st.markdown(f"**{title}**")
    st.dataframe(df[keep], use_container_width=True, hide_index=True, height=frame_height(len(df), base=72, row=34, max_height=300))


def render_forward_radar_panel(rows: list[dict], title: str = 'Forward-Looking') -> None:
    st.subheader(title)
    if not rows:
        st.info('Belum ada nama yang masuk forward radar.')
        return

    df = _prep(rows)
    if 'side' in df.columns:
        long_df = df[df['side'].str.lower() == 'long'].sort_values(['edge','score'], ascending=[False, False])
        short_df = df[df['side'].str.lower() == 'short'].sort_values(['edge','score'], ascending=[False, True])
        neutral_df = df[~df['side'].str.lower().isin(['long','short'])].sort_values(['edge','score'], ascending=[False, False])
        cols = st.columns(2)
        with cols[0]:
            _show(long_df, 'Radar long · paling menarik → biasa aja')
        with cols[1]:
            _show(short_df, 'Radar short · paling rapuh → biasa aja')
        if not neutral_df.empty:
            _show(neutral_df, 'Radar mixed / tactical')
    else:
        df = df.sort_values(['edge','score'], ascending=[False, False])
        _show(df, 'Prioritas radar tertinggi')
