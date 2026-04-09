from __future__ import annotations
import streamlit as st


def render_regime_ribbon(shared_core: dict) -> None:
    ribbon = shared_core.get('status_ribbon', {}) or {}
    structural = ribbon.get('structural_quad', ribbon.get('current_quad', '-'))
    monthly = ribbon.get('monthly_quad', structural)
    resolved_language = ribbon.get('resolved_language', ribbon.get('operating_regime', f"Aligned {structural}"))
    dominant = ribbon.get('dominant_horizon', 'aligned')
    health = ribbon.get('health', '-')
    risk_off = ribbon.get('risk_off', '-')
    crash = ribbon.get('crash', '-')
    confidence = float(ribbon.get('confidence', 0.0) or 0.0)
    band = str(ribbon.get('confidence_band', 'low'))
    cols = st.columns(6, gap='small')
    cols[0].metric('Structural Quad', structural)
    cols[1].metric('Monthly Quad', monthly)
    cols[2].metric('Operating Regime', resolved_language)
    cols[3].metric('Dominant Horizon', dominant)
    cols[4].metric('Confidence', f"{100 * confidence:.0f}% · {band}")
    cols[5].metric('Health / Risk', f"{health} · {risk_off}/{crash}")
