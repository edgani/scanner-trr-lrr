from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from config.display_names import display_symbol
from scanner.sanity import snapshot_market_is_ready

ROOT = Path(__file__).resolve().parent
SCAN_DIR = ROOT / 'data' / 'scans'
MACRO_FILE = ROOT / 'data' / 'macro' / 'scanner_brain.json'

st.set_page_config(page_title='Scanner Final v33', layout='wide')


HORIZON_MAP = {
    'short_term': 'Short Term',
    'mid_term': 'Mid Term',
    'long_term': 'Long Term',
    'next_play': 'Next Plays',
    'next_plays': 'Next Plays',
    'short': 'Short Term',
    'mid': 'Mid Term',
    'long': 'Long Term',
    'next': 'Next Plays',
}


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def load_manifest(market: str) -> dict:
    return load_json(SCAN_DIR / f'{market}_scanner_manifest.json')


def load_snapshot(market: str) -> pd.DataFrame:
    p = SCAN_DIR / f'{market}_scanner_snapshot.csv'
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    if df.empty:
        return df
    if 'display_symbol' not in df.columns:
        df['display_symbol'] = df.get('symbol', pd.Series(dtype=str)).map(display_symbol)
    if 'horizon_bucket' in df.columns:
        df['horizon_label'] = df['horizon_bucket'].astype(str).map(lambda x: HORIZON_MAP.get(x, x))
    else:
        df['horizon_label'] = 'Unknown'
    if 'long_or_short' in df.columns:
        df['side_label'] = df['long_or_short'].astype(str).str.title()
    else:
        df['side_label'] = 'Long'
    if 'ev_rr' not in df.columns and {'ev_score', 'rr_score'}.issubset(df.columns):
        df['ev_rr'] = df['ev_score'].round(2).astype(str) + ' / ' + df['rr_score'].round(2).astype(str)
    return df


def show_table(df: pd.DataFrame, key_prefix: str) -> None:
    if df.empty:
        st.info('Tidak ada kandidat di bucket ini.')
        return
    cols = ['display_symbol', 'bias', 'entry_zone', 'invalidation', 'target', 'holding_window', 'macro_aligned', 'ev_rr']
    view = df[cols].copy().rename(columns={
        'display_symbol': 'Ticker',
        'bias': 'Bias',
        'entry_zone': 'Entry Zone',
        'invalidation': 'Invalidation',
        'target': 'Target',
        'holding_window': 'Holding Window',
        'macro_aligned': 'Macro Aligned?',
        'ev_rr': 'EV+ / R:R',
    })
    st.dataframe(view, use_container_width=True, hide_index=True)
    pick = st.selectbox('Detail ticker', options=view['Ticker'].tolist(), key=f'pick_{key_prefix}')
    row = df.loc[df['display_symbol'] == pick].iloc[0]
    st.markdown(f'**{pick}**')
    st.write(f"Alasan: {row.get('why_now') or row.get('why_not_yet') or '-'}")
    st.write(f"Route: {row.get('route', '-')}")
    st.write(f"Macro explanation: {row.get('macro_explanation', '-')}")
    if row.get('why_not_yet'):
        st.write(f"Why not yet: {row.get('why_not_yet')}")


market = st.sidebar.selectbox('Market', ['us', 'ihsg', 'forex', 'commodities', 'crypto'])
macro = load_json(MACRO_FILE)
man = load_manifest(market)
df = load_snapshot(market)
market_ready, market_reason = snapshot_market_is_ready(man)
if not market_ready:
    df = pd.DataFrame()

st.title('Scanner Final v33')

c1, c2, c3, c4 = st.columns(4)
c1.metric('Universe', int(man.get('universe_count', 0) or 0))
c2.metric('History loaded', int(man.get('history_loaded', 0) or 0))
c3.metric('Eligible', int(man.get('eligible_count', 0) or 0))
c4.metric('Rows', int(man.get('rows_count', len(df)) or 0))

with st.expander('Macro brain summary', expanded=False):
    st.json({
        'current_quad': macro.get('current_quad'),
        'current_route': macro.get('current_route'),
        'next_route': ((macro.get('market_brains', {}) or {}).get(market) or {}).get('next_route') or macro.get('next_route'),
        'invalidator_route': ((macro.get('market_brains', {}) or {}).get(market) or {}).get('invalidator_route') or macro.get('invalidator_route'),
        'execution_mode': ((macro.get('market_brains', {}) or {}).get(market) or {}).get('execution_mode') or (macro.get('execution_mode', {}) or {}).get('label'),
        'shock_state': macro.get('shock_state'),
        'market_health': macro.get('market_health'),
        'crash_state': macro.get('crash_state'),
        'safe_harbor': macro.get('safe_harbor'),
        'best_beneficiary': macro.get('best_beneficiary'),
    })

if not market_ready:
    st.warning(market_reason)
    st.info('App sengaja snapshot-only dan tidak akan fetch live saat page load.')
elif df.empty:
    st.warning('Snapshot ada, tapi semua kandidat gugur di filter saat ini.')
else:
    if int(man.get('sanity_rejected_count', 0) or 0) > 0:
        st.info(f"{int(man.get('sanity_rejected_count', 0) or 0)} ticker ditolak oleh stale/absurd sanity-check builder.")
    tabs = st.tabs(['Short Term', 'Mid Term', 'Long Term', 'Next Plays'])
    for horizon, tab in zip(['Short Term', 'Mid Term', 'Long Term', 'Next Plays'], tabs):
        with tab:
            left, right = st.columns(2)
            with left:
                st.subheader('Long')
                show_table(df[(df['horizon_label'] == horizon) & (df['side_label'] == 'Long')], key_prefix=f'{market}_{horizon}_long')
            with right:
                st.subheader('Short')
                show_table(df[(df['horizon_label'] == horizon) & (df['side_label'] == 'Short')], key_prefix=f'{market}_{horizon}_short')
