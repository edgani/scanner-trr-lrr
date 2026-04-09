from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.components.compact_table_helpers import frame_height
from utils.streamlit_utils import info_card


def _kv_lines(d: dict, keys: list[str]) -> list[str]:
    out = []
    for k in keys:
        if k in d:
            out.append(f"{k}: {d.get(k)}")
    return out


def _flat_rows(d: dict, prefix: str = '') -> list[dict]:
    rows = []
    for k, v in (d or {}).items():
        name = f"{prefix}{k}"
        if isinstance(v, dict):
            rows.extend(_flat_rows(v, prefix=name + '.'))
        else:
            rows.append({'field': name, 'value': v})
    return rows


def _show_rows(rows: list[dict], max_height: int = 240) -> None:
    if not rows:
        st.caption('No data')
        return
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True, height=frame_height(len(df), base=72, row=30, max_height=max_height))


def render_diagnostics_page(snapshot: dict) -> None:
    st.title('Diagnostics')
    sec = snapshot.get('diagnostics', {})
    shared = snapshot.get('shared_core', {}) or {}
    regime_stack = shared.get('regime_stack', {}) or {}
    next_path = shared.get('next_path', {}) or {}
    integrity = shared.get('integrity', {}) or {}

    t1, t2, t3, t4, t5 = st.tabs(['Regime', 'Coverage', 'Scenario', 'Analogs', 'Ops'])
    with t1:
        _show_rows(_flat_rows({'structural': regime_stack.get('structural', {}), 'monthly': regime_stack.get('monthly', {}), 'resolved': regime_stack.get('resolved', {})}), max_height=320)
        info_card('Confidence', _kv_lines({
            'confidence_band': shared.get('resolved_regime', {}).get('confidence_band', '-'),
            'resolved_language': shared.get('resolved_regime', {}).get('resolved_language', '-'),
            'quad_divergence': integrity.get('quad_divergence', '-'),
            'breadth_state': integrity.get('breadth_state', '-'),
            'breadth_trend': integrity.get('breadth_trend', '-'),
            'macro_proxy_share': integrity.get('macro_proxy_share', 0.0),
            'macro_conf_penalty': integrity.get('macro_confidence_penalty', 0.0),
        }, ['confidence_band', 'resolved_language', 'quad_divergence', 'breadth_state', 'breadth_trend', 'macro_proxy_share', 'macro_conf_penalty']), accent='#365b46')
        _show_rows(_flat_rows(next_path), max_height=240)
    with t2:
        _show_rows(_flat_rows({'shared': sec.get('shared_feature_coverage', {}), 'native': sec.get('native_feature_coverage', {}), 'integrity': integrity}), max_height=360)
        coverage = sec.get('coverage_reports', {}) or {}
        if coverage:
            rows = []
            for market, rep in coverage.items():
                rows.append({
                    'market': market.upper(),
                    'bucket': int(rep.get('bucket_universe_size', 0) or 0),
                    'backend': int(rep.get('backend_universe_size', 0) or 0),
                    'ranking': int(rep.get('ranking_universe_size', 0) or 0),
                    'unbucketed': len(rep.get('unbucketed_symbols', []) or []),
                    'sample_unbucketed': ', '.join((rep.get('unbucketed_symbols', []) or [])[:6]),
                })
            st.markdown('**Routing coverage audit**')
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=frame_height(len(rows), base=72, row=30, max_height=260))
    with t3:
        impact_map = sec.get('scenario_tab_impact_map', []) or []
        if impact_map:
            df = pd.DataFrame(impact_map)
            st.dataframe(df, use_container_width=True, hide_index=True, height=frame_height(len(df), base=72, row=30, max_height=300))
        _show_rows(_flat_rows(sec.get('news_state', {})), max_height=220)
    with t4:
        _show_rows(_flat_rows(sec.get('historical_analog_state', {})), max_height=260)
        _show_rows(_flat_rows(sec.get('validation', {})), max_height=220)
    with t5:
        _show_rows(_flat_rows(sec.get('price_info', {})), max_height=220)
        _show_rows(_flat_rows(sec.get('macro_calendar', {})), max_height=220)
