
from __future__ import annotations

import html
import streamlit as st


def _crop(text: str, n: int = 52) -> str:
    text = ' '.join(str(text or '').split())
    return text if len(text) <= n else text[: max(0, n - 1)].rstrip() + '…'


def _flow_digest(flow: dict, fallback: str = '-') -> dict:
    if not flow:
        return {
            'headline': fallback,
            'summary': '',
            'sub': '',
            'tickers': [],
            'step_titles': [],
            'edge': '',
        }
    steps = flow.get('steps', []) or []
    titles = [str(s.get('title', '-')).strip() for s in steps if str(s.get('title', '')).strip()]
    headline = ' → '.join(titles[:2]) if titles else fallback
    summary = flow.get('summary', '') or flow.get('stage_now', '') or flow.get('stage_note', '') or ''
    sub = flow.get('stage_remaining', '') or flow.get('stage_note', '') or ''
    tickers = []
    for step in steps[:3]:
        for t in (step.get('tickers', []) or [])[:2]:
            t = str(t).strip()
            if t and t not in tickers:
                tickers.append(t)
    return {
        'headline': _crop(headline, 44),
        'summary': _crop(summary, 88),
        'sub': _crop(sub, 40),
        'tickers': tickers[:4],
        'step_titles': titles[:4],
        'edge': _crop(flow.get('summary', '') or flow.get('stage_note', '') or '', 72),
    }


def _neutral_palette(active: bool = False, warn: bool = False) -> tuple[str, str, str]:
    if active and warn:
        return ('#e8b14c', 'linear-gradient(180deg, rgba(232,177,76,.18), rgba(232,177,76,.06))', '0 0 0 1px rgba(232,177,76,.45), 0 0 24px rgba(232,177,76,.12)')
    if active:
        return ('#7db3ff', 'linear-gradient(180deg, rgba(125,179,255,.18), rgba(125,179,255,.06))', '0 0 0 1px rgba(125,179,255,.45), 0 0 24px rgba(125,179,255,.12)')
    return ('rgba(132,149,183,.45)', 'linear-gradient(180deg, rgba(22,30,45,.88), rgba(12,18,29,.96))', 'none')


def _tag(text: str, active: bool = False, tone: str = 'neutral') -> str:
    if active:
        border, bg, color = '#7db3ff', 'rgba(125,179,255,.15)', '#eaf2ff'
    elif tone == 'warn':
        border, bg, color = '#e8b14c', 'rgba(232,177,76,.12)', '#f9e4bb'
    elif tone == 'bad':
        border, bg, color = '#ce5b73', 'rgba(206,91,115,.12)', '#ffd7df'
    else:
        border, bg, color = 'rgba(132,149,183,.45)', 'rgba(255,255,255,.03)', '#bfcde2'
    return f"<span style='display:inline-block;padding:1px 7px;border-radius:999px;border:1px solid {border};background:{bg};color:{color};font-size:.58rem;font-weight:700;line-height:1.2;margin-right:4px;margin-top:4px'>{html.escape(_crop(text,16))}</span>"


def _node(label: str, digest: dict, *, active: bool = False, warn: bool = False, stage: str = '') -> str:
    border, bg, shadow = _neutral_palette(active=active, warn=warn)
    tags = ''.join(_tag(t, active=False) for t in digest.get('tickers', [])[:3]) or _tag('-', active=False)
    stage_text = f"<div style='font-size:.56rem;color:#9ab0cf;font-weight:800;letter-spacing:.05em;text-transform:uppercase'>{html.escape(stage)}</div>" if stage else ''
    return (
        f"<div style='border:1px solid {border};background:{bg};box-shadow:{shadow};border-radius:16px;padding:10px 10px 9px 10px;min-height:116px'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:8px'>"
        f"<div style='font-size:.58rem;color:#9ab0cf;font-weight:800;letter-spacing:.05em;text-transform:uppercase'>{html.escape(label)}</div>"
        f"{stage_text}</div>"
        f"<div style='font-size:.86rem;font-weight:900;line-height:1.08;margin-top:3px;color:#e9f1ff'>{html.escape(digest.get('headline','-'))}</div>"
        f"<div style='font-size:.67rem;color:#c6d3e7;line-height:1.18;margin-top:5px'>{html.escape(digest.get('summary','-'))}</div>"
        f"<div style='margin-top:6px'>{tags}</div>"
        f"</div>"
    )


def _edge(text: str, active: bool = False) -> str:
    color = '#7db3ff' if active else '#7b8ca8'
    note = html.escape(_crop(text or '-', 42))
    return (
        f"<div style='display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%'>"
        f"<div style='font-size:.56rem;color:{color};text-align:center;line-height:1.15;margin-bottom:2px'>{note}</div>"
        f"<div style='color:{color};font-size:1rem;font-weight:900'>→</div>"
        f"</div>"
    )


def _stage_index(dominant: str, flip_hazard: float) -> int:
    dominant = str(dominant or '').lower()
    if flip_hazard >= 0.68:
        return 4
    if dominant == 'structural':
        return 0
    if dominant == 'monthly':
        return 1
    return 2


def _stage_strip(current_idx: int, next_label: str = '-') -> str:
    labels = [
        ('1', 'Structural', 'backbone'),
        ('2', 'Monthly', 'overlay'),
        ('3', 'Resolved', 'used now'),
        ('4', 'Spillover', 'receivers'),
        ('5', 'Next', next_label or '-'),
    ]
    cells = []
    for idx, (num, title, sub) in enumerate(labels):
        active = idx == current_idx
        warn = idx == 4 and current_idx == 4
        border, bg, shadow = _neutral_palette(active=active, warn=warn)
        cells.append(
            f"<div style='border:1px solid {border};background:{bg};box-shadow:{shadow};border-radius:999px;padding:7px 10px;min-height:56px'>"
            f"<div style='font-size:.54rem;color:#9ab0cf;font-weight:800;text-transform:uppercase;letter-spacing:.05em'>Stage {num}</div>"
            f"<div style='font-size:.80rem;font-weight:900;line-height:1.05'>{title}</div>"
            f"<div style='font-size:.62rem;color:#c6d3e7'>{html.escape(_crop(sub, 20))}</div>"
            f"</div>"
        )
    return "<div style='display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin:2px 0 8px 0'>" + ''.join(cells) + "</div>"


def _legend(current_label: str, next_label: str, invalidators: list[str]) -> str:
    inv = '; '.join(_crop(x, 26) for x in (invalidators or [])[:2]) or '-'
    return (
        f"<div style='display:grid;grid-template-columns:1.05fr .95fr;gap:6px;margin-top:6px'>"
        f"<div style='border:1px solid rgba(132,149,183,.35);border-radius:12px;padding:8px 10px;background:rgba(255,255,255,.02)'>"
        f"<div style='font-size:.58rem;color:#9ab0cf;font-weight:800;text-transform:uppercase;letter-spacing:.05em'>You are here</div>"
        f"<div style='font-size:.74rem;font-weight:800;line-height:1.2'>{html.escape(current_label)}</div>"
        f"<div style='font-size:.66rem;color:#c6d3e7;margin-top:3px'>Next branch watch: {html.escape(_crop(next_label, 40))}</div>"
        f"</div>"
        f"<div style='border:1px solid rgba(132,149,183,.35);border-radius:12px;padding:8px 10px;background:rgba(255,255,255,.02)'>"
        f"<div style='font-size:.58rem;color:#9ab0cf;font-weight:800;text-transform:uppercase;letter-spacing:.05em'>Invalidators</div>"
        f"<div style='font-size:.66rem;color:#c6d3e7;line-height:1.15'>{html.escape(inv)}</div>"
        f"</div>"
        f"</div>"
    )


def render_market_correlated_map(grouped: dict[str, list[dict]], next_path: dict | None = None, title: str = 'Correlated Rotation Mind Map') -> None:
    next_path = next_path or {}
    struct_rot = _flow_digest((grouped.get('rotation_structural') or [{}])[0], 'Backbone rotation')
    month_rot = _flow_digest((grouped.get('rotation_monthly') or [{}])[0], 'Monthly rotation')
    resolved_rot = _flow_digest((grouped.get('rotation_resolved') or [{}])[0], 'Resolved execution')
    struct_sp = _flow_digest((grouped.get('spillover_structural') or [{}])[0], 'Structural spillover')
    month_sp = _flow_digest((grouped.get('spillover_monthly') or [{}])[0], 'Monthly trigger')
    resolved_sp = _flow_digest((grouped.get('spillover_resolved') or [{}])[0], 'Resolved spillover')

    dominant = str(next_path.get('dominant_horizon', next_path.get('confidence_band', 'resolved')))
    current_idx = _stage_index(dominant, float(next_path.get('flip_hazard', 0.0) or 0.0))
    next_label = str(next_path.get('next_resolved_regime', '-'))
    current_label = resolved_rot.get('headline', 'Resolved execution active')

    html_block = f"""
    <div style='margin:6px 0 10px 0'>
      <div style='font-size:.84rem;font-weight:900;margin-bottom:4px'>{html.escape(title)}</div>
      {_stage_strip(current_idx, next_label)}
      <div style='display:grid;grid-template-columns:1fr 42px 1fr 42px 1fr 42px 1fr;gap:6px;align-items:stretch'>
        <div>{_node('Structural rotation', struct_rot, active=current_idx==0, stage='backbone')}</div>
        {_edge('backbone sets the first receivers', active=current_idx in (0,1,2))}
        <div>{_node('Monthly rotation', month_rot, active=current_idx==1, stage='overlay')}</div>
        {_edge('monthly either broadens or narrows the route', active=current_idx in (1,2))}
        <div>{_node('Resolved execution', resolved_rot, active=current_idx==2, stage='used now')}</div>
        {_edge('resolved route hands off to the next branch', active=current_idx in (2,4))}
        <div>{_node('Next route', {'headline': next_label or '-', 'summary': next_path.get('continuation_path','-'), 'tickers': [x.get('quad','-') for x in (next_path.get('structural_candidates',[]) or [])[:2]], 'sub': ''}, active=current_idx==4, warn=True, stage='watch')}</div>
      </div>
      <div style='display:grid;grid-template-columns:1fr 42px 1fr 42px 1fr;gap:6px;align-items:stretch;margin-top:6px'>
        <div>{_node('Structural spillover', struct_sp, active=current_idx==3, stage='receivers')}</div>
        {_edge('structural route points to 2nd-order beneficiaries', active=current_idx>=2)}
        <div>{_node('Monthly trigger', month_sp, active=current_idx==3, stage='trigger')}</div>
        {_edge('trigger confirms or blocks the spillover', active=current_idx>=2)}
        <div>{_node('Resolved spillover', resolved_sp, active=current_idx==3, stage='confirmed')}</div>
      </div>
      {_legend(current_label, next_label, next_path.get('invalidators') or [])}
    </div>
    """
    st.markdown(html_block, unsafe_allow_html=True)


def render_dashboard_correlated_map(shared: dict, flows: list[dict], title: str = 'Global Correlated Rotation Mind Map') -> None:
    reg = shared.get('regime_stack', {}) or {}
    resolved = shared.get('resolved_regime', {}) or {}
    next_path = shared.get('next_path', {}) or {}
    rotation_stack = shared.get('flow_stack', {}).get('rotation', {}) or {}
    structural = {'headline': str((reg.get('structural') or {}).get('quad', '-')), 'summary': 'backbone regime', 'tickers': (rotation_stack.get('structural', {}) or {}).get('leaders', [])[:3]}
    monthly = {'headline': str((reg.get('monthly') or {}).get('quad', '-')), 'summary': 'monthly overlay', 'tickers': (rotation_stack.get('monthly', {}) or {}).get('leaders', [])[:3]}
    resolved_d = {'headline': str(resolved.get('resolved_language', resolved.get('operating_regime', '-'))), 'summary': str(resolved.get('dominant_horizon', '-')), 'tickers': (rotation_stack.get('resolved', {}) or {}).get('leaders', [])[:3]}
    next_d = {'headline': str(next_path.get('next_resolved_regime', '-')), 'summary': str(next_path.get('continuation_path', '-')), 'tickers': [x.get('quad', '-') for x in (next_path.get('structural_candidates', []) or [])[:2]]}
    long_flow = _flow_digest(flows[0] if len(flows) > 0 else {}, 'Long bias')
    short_flow = _flow_digest(flows[1] if len(flows) > 1 else {}, 'Short / hedge')
    escape_flow = _flow_digest(flows[2] if len(flows) > 2 else {}, 'Escape / safe harbor')
    current_idx = _stage_index(str(resolved.get('dominant_horizon', '-')), float(next_path.get('flip_hazard', 0.0) or 0.0))
    html_block = f"""
    <div style='margin:6px 0 10px 0'>
      <div style='font-size:.84rem;font-weight:900;margin-bottom:4px'>{html.escape(title)}</div>
      {_stage_strip(current_idx, str(next_path.get('next_resolved_regime', '-')))}
      <div style='display:grid;grid-template-columns:1fr 42px 1fr 42px 1fr 42px 1fr;gap:6px;align-items:stretch'>
        <div>{_node('Structural', structural, active=current_idx==0, stage='backbone')}</div>
        {_edge('monthly tests whether backbone broadens', active=current_idx in (0,1,2))}
        <div>{_node('Monthly', monthly, active=current_idx==1, stage='overlay')}</div>
        {_edge('resolved route chooses what to trade now', active=current_idx in (1,2))}
        <div>{_node('Resolved', resolved_d, active=current_idx==2, stage='used now')}</div>
        {_edge('next branch if continuation fails or broadens', active=current_idx in (2,4))}
        <div>{_node('Next', next_d, active=current_idx==4, warn=True, stage='watch')}</div>
      </div>
      <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;align-items:stretch;margin-top:6px'>
        <div>{_node('Long bias', long_flow, active=False, stage='receiver')}</div>
        <div>{_node('Short / hedge', short_flow, active=False, stage='risk')}</div>
        <div>{_node('Escape / shelter', escape_flow, active=False, stage='safety')}</div>
      </div>
      {_legend(str(resolved.get('resolved_language', '-')), str(next_path.get('next_resolved_regime', '-')), next_path.get('invalidators') or [])}
    </div>
    """
    st.markdown(html_block, unsafe_allow_html=True)


def render_scenario_correlation_map(sec: dict, title: str = 'Scenario Correlation Mind Map') -> None:
    structural = {'headline': str(sec.get('structural_quad', sec.get('current_quad', '-'))), 'summary': 'backbone scenario regime', 'tickers': []}
    monthly = {'headline': str(sec.get('monthly_quad', '-')), 'summary': str(sec.get('divergence_state', '-')), 'tickers': []}
    scenario_family = (sec.get('scenario_family', []) or ['-'])
    base = {'headline': str(scenario_family[0]), 'summary': 'priority branch now', 'tickers': []}
    next_p = sec.get('next_path', {}) or {}
    next_d = {'headline': str(next_p.get('next_resolved_regime', '-')), 'summary': str(next_p.get('continuation_path', '-')), 'tickers': [str(sec.get('next_macro_family', '-'))]}
    current_idx = _stage_index(str(sec.get('dominant_horizon', '-')), float(next_p.get('flip_hazard', 0.0) or 0.0))
    html_block = f"""
    <div style='margin:6px 0 10px 0'>
      <div style='font-size:.84rem;font-weight:900;margin-bottom:4px'>{html.escape(title)}</div>
      {_stage_strip(current_idx, str(next_p.get('next_resolved_regime', '-')))}
      <div style='display:grid;grid-template-columns:1fr 42px 1fr 42px 1fr 42px 1fr;gap:6px;align-items:stretch'>
        <div>{_node('Structural', structural, active=current_idx==0, stage='backbone')}</div>
        {_edge('monthly divergence tells whether branch is tactical or structural', active=current_idx in (0,1,2))}
        <div>{_node('Monthly', monthly, active=current_idx==1, stage='overlay')}</div>
        {_edge('base branch selected from structural + monthly mix', active=current_idx in (1,2))}
        <div>{_node('Base branch', base, active=current_idx==2, stage='scenario')}</div>
        {_edge('next branch if catalyst forces a handoff', active=current_idx in (2,4))}
        <div>{_node('Next branch', next_d, active=current_idx==4, warn=True, stage='watch')}</div>
      </div>
      {_legend(str(base.get('headline','-')), str(next_p.get('next_resolved_regime', '-')), next_p.get('invalidators') or [])}
    </div>
    """
    st.markdown(html_block, unsafe_allow_html=True)


def render_cross_asset_correlation_map(sec: dict, shared: dict, title: str = 'Cross-Asset Correlation Mind Map') -> None:
    regime = shared.get('regime_stack', {}) or {}
    resolved = regime.get('resolved', {}) or {}
    next_path = shared.get('next_path', {}) or {}
    em = sec.get('em_rotation', {}) or {}
    petro = sec.get('petrodollar', {}) or {}
    structural = {'headline': str((regime.get('structural') or {}).get('quad','-')), 'summary': 'global backbone', 'tickers': []}
    monthly = {'headline': str((regime.get('monthly') or {}).get('quad','-')), 'summary': 'cross-asset overlay', 'tickers': []}
    operating = {'headline': str(resolved.get('resolved_language','-')), 'summary': str(resolved.get('dominant_horizon','-')), 'tickers': []}
    nxt = {'headline': str(next_path.get('next_resolved_regime','-')), 'summary': str(next_path.get('continuation_path','-')), 'tickers': []}
    current_idx = _stage_index(str(resolved.get('dominant_horizon', '-')), float(next_path.get('flip_hazard', 0.0) or 0.0))
    html_block = f"""
    <div style='margin:6px 0 10px 0'>
      <div style='font-size:.84rem;font-weight:900;margin-bottom:4px'>{html.escape(title)}</div>
      {_stage_strip(current_idx, str(next_path.get('next_resolved_regime', '-')))}
      <div style='display:grid;grid-template-columns:1fr 42px 1fr 42px 1fr 42px 1fr;gap:6px;align-items:stretch'>
        <div>{_node('Structural', structural, active=current_idx==0, stage='backbone')}</div>
        {_edge('monthly tells whether route broadens or narrows', active=current_idx in (0,1,2))}
        <div>{_node('Monthly', monthly, active=current_idx==1, stage='overlay')}</div>
        {_edge('operating route maps winners, hedges, shelters', active=current_idx in (1,2))}
        <div>{_node('Operating', operating, active=current_idx==2, stage='used now')}</div>
        {_edge('next route points to broadening or breakdown', active=current_idx in (2,4))}
        <div>{_node('Next', nxt, active=current_idx==4, warn=True, stage='watch')}</div>
      </div>
      <div style='display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:6px;align-items:stretch;margin-top:6px'>
        <div>{_node('Conflict / confirm', {'headline': 'signal + breadth', 'summary': str(sec.get('conflict_map', {}))[:80], 'tickers': []}, active=False, stage='check')}</div>
        <div>{_node('Rotation / safe harbor', {'headline': ', '.join((sec.get('rotation', {}) or {}).get('resolved_rotation', {}).get('leaders', [])[:2]) or '-', 'summary': 'resolved leaders / shelters', 'tickers': ((sec.get('rotation', {}) or {}).get('resolved_rotation', {}) or {}).get('safe_harbors', [])[:3]}, active=False, stage='map')}</div>
        <div>{_node('EM rotation', {'headline': str(em.get('resolved_state', '-')), 'summary': str(em.get('next_route', '-')), 'tickers': []}, active=False, stage='regional')}</div>
        <div>{_node('Petrodollar', {'headline': str(petro.get('state', 'normal')), 'summary': str(petro.get('next_route', '-')), 'tickers': []}, active=False, stage='macro')}</div>
      </div>
      {_legend(str(operating.get('headline','-')), str(next_path.get('next_resolved_regime', '-')), next_path.get('invalidators') or [])}
    </div>
    """
    st.markdown(html_block, unsafe_allow_html=True)
