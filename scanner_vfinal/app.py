from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from config.display_names import display_symbol

ROOT = Path(__file__).resolve().parent
SCAN_DIR = ROOT / 'data' / 'scans'
MACRO_FILE = ROOT / 'data' / 'macro' / 'latest_macro_snapshot.json'

st.set_page_config(page_title='Scanner Final v33', layout='wide')


def load_macro() -> dict:
    if not MACRO_FILE.exists():
        return {}
    return json.loads(MACRO_FILE.read_text(encoding='utf-8'))


def load_snapshot(market: str) -> pd.DataFrame:
    p = SCAN_DIR / f"{market}_scanner_snapshot.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


def load_manifest(market: str) -> dict:
    p = SCAN_DIR / f"{market}_scanner_manifest.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding='utf-8'))


def show_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.info('Tidak ada kandidat di bucket ini.')
        return
    cols = ['display_symbol', 'bias', 'entry_zone', 'invalidation', 'target', 'holding_window', 'macro_aligned', 'rr_score']
    view = df[cols].copy().rename(columns={'display_symbol': 'Ticker', 'rr_score': 'EV+ / R:R', 'holding_window': 'Holding Window', 'entry_zone': 'Entry Zone', 'macro_aligned': 'Macro Aligned?', 'invalidation': 'Invalidation', 'target': 'Target', 'bias': 'Bias'})
    st.dataframe(view, use_container_width=True, hide_index=True)
    pick = st.selectbox('Detail ticker', options=view['Ticker'].tolist(), key=f"pick_{hash(tuple(view['Ticker']))}")
    row = df.loc[df['display_symbol'] == pick].iloc[0]
    st.markdown(f"**{pick}**")
    st.write(f"Alasan: {row.get('why_now') or row.get('why_not_yet') or '-'}")
    st.write(f"Route: {row.get('route', '-')}")
    st.write(f"Macro explanation: {row.get('macro_explanation', '-')}")
    if row.get('why_not_yet'):
        st.write(f"Why not yet: {row.get('why_not_yet')}")


market = st.sidebar.selectbox('Market', ['us', 'ihsg', 'forex', 'commodities', 'crypto'])
macro = load_macro()
man = load_manifest(market)
df = load_snapshot(market)

st.title('Scanner Final v33')

c1, c2, c3, c4 = st.columns(4)
c1.metric('Universe', man.get('universe_count', 0))
c2.metric('History loaded', man.get('history_loaded', 0))
c3.metric('Eligible', man.get('eligible_count', 0))
c4.metric('Rows', man.get('rows_count', 0))

with st.expander('Macro brain summary', expanded=True):
    st.write({
        'current_quad': macro.get('current_quad'),
        'next_quad': macro.get('next_quad'),
        'execution_mode': macro.get('execution_mode'),
        'safe_harbor': macro.get('safe_harbor'),
        'best_beneficiary': macro.get('best_beneficiary'),
    })

if man.get('history_loaded', 0) == 0:
    st.warning('Pack ini deploy-ready, tapi market ini belum punya starter snapshot yang terisi. Jalankan builder lokal/VPS untuk mengisi market ini.')

if df.empty:
    st.info('Snapshot kosong untuk market ini.')
else:
    tabs = st.tabs(['Short Term', 'Mid Term', 'Long Term', 'Next Plays'])
    for horizon, tab in zip(['short', 'mid', 'long', 'next'], tabs):
        with tab:
            left, right = st.columns(2)
            with left:
                st.subheader('Long')
                show_table(df[(df['horizon_bucket'] == horizon) & (df['long_or_short'] == 'long')])
            with right:
                st.subheader('Short')
                show_table(df[(df['horizon_bucket'] == horizon) & (df['long_or_short'] == 'short')])
