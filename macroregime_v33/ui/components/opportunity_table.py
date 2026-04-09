from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.components.compact_table_helpers import frame_height

DEFAULT_COLS = [
    'ticker', 'market', 'bias', 'horizon', 'entry_zone', 'invalidation', 'target',
    'countdown_days_left', 'review_state', 'next_action', 'macro_aligned',
    'route_source_label', 'confidence', 'ev_score'
]


_RENAME = {
    'ticker': 'Ticker',
    'market': 'Market',
    'bias': 'Bias',
    'horizon': 'Horizon',
    'entry_zone': 'Entry zone',
    'invalidation': 'Invalidation',
    'target': 'Target',
    'countdown_days_left': 'Countdown',
    'review_state': 'Review',
    'next_action': 'Next action',
    'macro_aligned': 'Macro aligned',
    'route_source_label': 'Route source',
    'confidence': 'Conf',
    'ev_score': 'EV',
    'why_now': 'Why now',
    'market_context_summary': 'Market context',
    'microstructure_flag': 'Microstructure',
    'structural_penalty_note': 'Structural note',
}


def _frame(rows: list[dict], cols: list[str] | None = None) -> pd.DataFrame:
    df = pd.DataFrame(rows or []).copy()
    if df.empty:
        return df
    cols = cols or DEFAULT_COLS
    keep = [c for c in cols if c in df.columns]
    df = df[keep]
    if 'confidence' in df.columns:
        df['confidence'] = pd.to_numeric(df['confidence'], errors='coerce').fillna(0.0).map(lambda x: f"{x:.2f}")
    if 'ev_score' in df.columns:
        df['ev_score'] = pd.to_numeric(df['ev_score'], errors='coerce').fillna(0.0).map(lambda x: f"{x:.2f}")
    if 'countdown_days_left' in df.columns:
        df['countdown_days_left'] = df['countdown_days_left'].map(lambda x: '-' if pd.isna(x) else f"{int(x)}D")
    if 'microstructure_flag' in df.columns:
        df['microstructure_flag'] = df['microstructure_flag'].fillna('').map(lambda x: str(x)[:72])
    if 'structural_penalty_note' in df.columns:
        df['structural_penalty_note'] = df['structural_penalty_note'].fillna('').map(lambda x: str(x)[:72])
    if 'why_now' in df.columns:
        df['why_now'] = df['why_now'].fillna('').map(lambda x: str(x)[:120])
    if 'market_context_summary' in df.columns:
        df['market_context_summary'] = df['market_context_summary'].fillna('').map(lambda x: str(x)[:120])
    df = df.rename(columns={k: v for k, v in _RENAME.items() if k in df.columns})
    return df


def render_opportunity_table(rows: list[dict], title: str, cols: list[str] | None = None, empty_msg: str = 'Belum ada row.') -> None:
    st.subheader(title)
    if not rows:
        st.info(empty_msg)
        return
    df = _frame(rows, cols)
    st.dataframe(df, use_container_width=True, hide_index=True, height=frame_height(len(df), base=90, row=36, max_height=420))
