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
    if 'microstructure_flag' in df.columns:
        df['microstructure_flag'] = df['microstructure_flag'].fillna('').map(lambda x: str(x)[:48])
    if 'why_now' in df.columns:
        df['why_now'] = df['why_now'].fillna('').map(lambda x: str(x)[:110])
    for col, limit in [('entry_zone', 48), ('t1_t2', 42), ('signal_quality', 24), ('invalidator', 56)]:
        if col in df.columns:
            df[col] = df[col].fillna('').map(lambda x, lim=limit: str(x)[:lim])
    return df


def _show(df: pd.DataFrame, title: str) -> None:
    if df.empty:
        return
    keep = [c for c in ['name','bucket','side','score','entry_zone','t1_t2','why_now','signal_quality','microstructure_flag','action','invalidator','risk','setup_type'] if c in df.columns]
    st.markdown(f"**{title}**")
    st.dataframe(df[keep], use_container_width=True, hide_index=True, height=frame_height(len(df), base=72, row=34, max_height=320))


def render_current_setups_panel(rows: list[dict], title: str = 'Setup Sekarang') -> None:
    st.subheader(title)
    if not rows:
        st.info('Belum ada setup yang lolos filter.')
        return

    df = _prep(rows)
    if 'side' in df.columns:
        long_df = df[df['side'].str.lower() == 'long'].sort_values(['edge','score'], ascending=[False, False])
        short_df = df[df['side'].str.lower() == 'short'].sort_values(['edge','score'], ascending=[False, True])
        neutral_df = df[~df['side'].str.lower().isin(['long','short'])].sort_values(['edge','score'], ascending=[False, False])

        cols = st.columns(2)
        with cols[0]:
            _show(long_df, 'Long bias · paling strong → biasa aja')
        with cols[1]:
            _show(short_df, 'Short bias · paling weak → biasa aja')
        if not neutral_df.empty:
            _show(neutral_df, 'Tactical / mixed')
    else:
        df = df.sort_values(['edge','score'], ascending=[False, False])
        _show(df, 'Prioritas tertinggi → lebih biasa')
