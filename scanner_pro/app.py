from __future__ import annotations
import pandas as pd
import streamlit as st
from config.settings import APP_TITLE, APP_SUBTITLE, MARKET_LABELS, MARKET_ORDER, SIMPLE_TABLE_COLUMNS
from scanner.snapshot_store import load_snapshot

st.set_page_config(page_title=APP_TITLE, layout='wide')

TOP_TABS = [
    ('short_term', 'Short Term'),
    ('mid_term', 'Mid Term'),
    ('long_term', 'Long Term'),
    ('next_play', 'Next Plays'),
]

def _human_countdown(value: str) -> str:
    if not value:
        return '-'
    text = str(value)
    return text.replace('T-', '').replace('Released', 'Sudah rilis')

def _show_table(df: pd.DataFrame, key: str):
    if df.empty:
        st.info('Belum ada ticker yang lolos filter di bucket ini.')
        return
    show = df[SIMPLE_TABLE_COLUMNS].copy()
    st.dataframe(show, use_container_width=True, hide_index=True)
    with st.expander('Detail ticker'):
        pick = st.selectbox('Pilih ticker', options=df['Ticker'].tolist(), key=f'detail_{key}')
        row = df[df['Ticker'] == pick].iloc[0].to_dict()
        left, right = st.columns(2)
        with left:
            st.markdown(f"**Alasan**: {row.get('why_now') or '-'}")
            st.markdown(f"**Route**: {row.get('route') or '-'}")
            st.markdown(f"**Macro explanation**: {row.get('macro_explanation') or '-'}")
            st.markdown(f"**Why not yet**: {row.get('why_not_yet') or '-'}")
        with right:
            st.markdown(f"**Current price**: {row.get('current_price', '-')}")
            st.markdown(f"**Raw states**: {row.get('raw_states', '-')}")
            st.markdown(f"**EV score**: {row.get('ev_score', '-')}")
            st.markdown(f"**R:R score**: {row.get('rr_score', '-')}")
            st.markdown(f"**Macro aligned?**: {row.get('Macro Aligned?', '-')}")
            st.markdown(f"**Type**: {'Next Play' if int(row.get('next_flag', 0)) == 1 else 'Execute Now'}")

st.title(APP_TITLE)
st.caption(APP_SUBTITLE)

with st.sidebar:
    market = st.selectbox('Pilih market', options=MARKET_ORDER, format_func=lambda x: MARKET_LABELS[x])
    min_ev = st.slider('Minimum EV score', 0.0, 5.0, 0.0, 0.1)
    show_mixed_macro = st.toggle('Tampilkan Macro Mixed', value=True)

snapshot, manifest = load_snapshot(market)
if snapshot is None or snapshot.empty:
    st.error('Snapshot belum ada atau kosong. Jalankan scripts/update_full_history.py lalu scripts/build_all_snapshots.py.')
    st.stop()

snapshot = snapshot.copy()
snapshot = snapshot[snapshot['ev_score'] >= min_ev]
if not show_mixed_macro:
    snapshot = snapshot[snapshot['Macro Aligned?'] == 'Yes']

macro = manifest.get('macro_overlay', {}) or {}
hist = manifest.get('history_status', {}) or {}
c1, c2, c3, c4 = st.columns(4)
c1.metric('Universe', manifest.get('universe', '-'))
c2.metric('History ready', hist.get('present', '-'))
c3.metric('Rows shown', len(snapshot))
c4.metric('Snapshot as-of', (manifest.get('as_of', '') or '')[:16].replace('T', ' '))

st.markdown(
    f"**Macro backdrop**: {macro.get('summary') or macro.get('market_bias') or '-'}  
"
    f"**Waktu ke event penting**: {_human_countdown(macro.get('next_macro_countdown', '-'))}  
"
    f"**Fokus berikutnya**: {macro.get('next_macro_focus') or '-'}"
)

top_tabs = st.tabs([label for _, label in TOP_TABS])
for tab, (bucket, label) in zip(top_tabs, TOP_TABS):
    with tab:
        long_df = snapshot[(snapshot['horizon_bucket'] == bucket) & (snapshot['long_or_short'] == 'Long')].sort_values(['ev_score','rr_score'], ascending=False)
        short_df = snapshot[(snapshot['horizon_bucket'] == bucket) & (snapshot['long_or_short'] == 'Short')].sort_values(['ev_score','rr_score'], ascending=False)
        sub1, sub2 = st.tabs(['Long', 'Short'])
        with sub1:
            _show_table(long_df, f'{bucket}_long')
        with sub2:
            _show_table(short_df, f'{bucket}_short')
