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

FOREX_DISPLAY_MAP = {
    'EURUSD=X': 'EUR/USD',
    'GBPUSD=X': 'GBP/USD',
    'AUDUSD=X': 'AUD/USD',
    'NZDUSD=X': 'NZD/USD',
    'JPY=X': 'USD/JPY',
    'CHF=X': 'USD/CHF',
    'CAD=X': 'USD/CAD',
    'EURJPY=X': 'EUR/JPY',
    'GBPJPY=X': 'GBP/JPY',
    'AUDJPY=X': 'AUD/JPY',
    'NZDJPY=X': 'NZD/JPY',
    'EURGBP=X': 'EUR/GBP',
    'EURCHF=X': 'EUR/CHF',
    'IDR=X': 'USD/IDR',
    'CNH=X': 'USD/CNH',
    'SGD=X': 'USD/SGD',
}
COMMODITY_DISPLAY_MAP = {
    'GC=F': 'XAUUSD',
    'SI=F': 'XAGUSD',
    'CL=F': 'USOIL',
}


def _human_countdown(value: str) -> str:
    if not value:
        return '-'
    text = str(value)
    return text.replace('T-', '').replace('Released', 'Sudah rilis')


def _display_ticker(symbol: str, market: str) -> str:
    sym = str(symbol)
    if market == 'forex':
        return FOREX_DISPLAY_MAP.get(sym, sym)
    if market == 'commodities':
        return COMMODITY_DISPLAY_MAP.get(sym, sym)
    if market == 'crypto' and sym.endswith('-USD'):
        return sym.replace('-USD', '/USD')
    return sym


def _prepare_display(df: pd.DataFrame, market: str) -> pd.DataFrame:
    out = df.copy()
    if 'Ticker' in out.columns:
        out['Ticker'] = out['Ticker'].map(lambda x: _display_ticker(x, market))
    if 'EV+ / R:R' not in out.columns and {'ev_score', 'rr_score'}.issubset(out.columns):
        out['EV+ / R:R'] = out.apply(lambda r: f"EV {r['ev_score']:.2f} | RR {r['rr_score']:.2f}", axis=1)
    return out


def _show_table(df: pd.DataFrame, key: str, market: str):
    if df.empty:
        st.info('Belum ada ticker yang lolos filter di bucket ini.')
        return
    view = _prepare_display(df, market)
    show = view[SIMPLE_TABLE_COLUMNS].copy()
    st.dataframe(show, use_container_width=True, hide_index=True)
    with st.expander('Detail ticker'):
        picks = view['Ticker'].tolist()
        pick = st.selectbox('Pilih ticker', options=picks, key=f'detail_{key}')
        row = view[view['Ticker'] == pick].iloc[0].to_dict()
        left, right = st.columns(2)
        with left:
            st.markdown(
    f"**Macro backdrop**: {macro.get('summary') or macro.get('market_bias') or '-'}\n\n"
    f"**Waktu ke event penting**: {_human_countdown(macro.get('next_macro_countdown', '-'))}\n\n"
    f"**Fokus berikutnya**: {macro.get('next_macro_focus') or '-'}"
)


top_tabs = st.tabs([label for _, label in TOP_TABS])
for tab, (bucket, label) in zip(top_tabs, TOP_TABS):
    with tab:
        long_df = snapshot[(snapshot['horizon_bucket'] == bucket) & (snapshot['long_or_short'] == 'Long')].sort_values(['ev_score', 'rr_score'], ascending=False)
        short_df = snapshot[(snapshot['horizon_bucket'] == bucket) & (snapshot['long_or_short'] == 'Short')].sort_values(['ev_score', 'rr_score'], ascending=False)
        sub1, sub2 = st.tabs(['Long', 'Short'])
        with sub1:
            _show_table(long_df, f'{bucket}_long', market)
        with sub2:
            _show_table(short_df, f'{bucket}_short', market)
