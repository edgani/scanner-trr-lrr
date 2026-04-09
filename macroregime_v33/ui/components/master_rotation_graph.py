from __future__ import annotations

import html
import streamlit as st


def _tag(text: str, tone: str = 'neutral') -> str:
    palette = {
        'neutral': ('rgba(132,149,183,.45)', 'rgba(255,255,255,.03)', '#d8e4f3'),
        'active': ('#7db3ff', 'rgba(125,179,255,.12)', '#eef5ff'),
        'warn': ('#e8b14c', 'rgba(232,177,76,.12)', '#f9e4bb'),
        'bad': ('#ce5b73', 'rgba(206,91,115,.12)', '#ffd7df'),
        'good': ('#39d98a', 'rgba(57,217,138,.10)', '#dcffef'),
    }
    b, bg, c = palette.get(tone, palette['neutral'])
    return f"<span style='display:inline-block;padding:1px 7px;border-radius:999px;border:1px solid {b};background:{bg};color:{c};font-size:.56rem;font-weight:700;line-height:1.2;margin-right:4px;margin-top:4px'>{html.escape(str(text))}</span>"


def _safe_text(value: object, fallback: str = '-') -> str:
    if value is None:
        return fallback
    if isinstance(value, (list, tuple, set)):
        joined = ', '.join(str(x) for x in value if x is not None)
        return joined or fallback
    if isinstance(value, dict):
        for key in ('label', 'state', 'name', 'summary', 'role'):
            if key in value and value.get(key) is not None:
                return str(value.get(key))
        return fallback
    text = str(value).strip()
    return text or fallback


def _node(title: str, label: object, summary: object, tickers: list[str] | None, *, active: bool = False, next_path: bool = False, danger: bool = False) -> str:
    if danger:
        border, bg, glow = '#ce5b73', 'linear-gradient(180deg, rgba(206,91,115,.16), rgba(206,91,115,.05))', '0 0 0 1px rgba(206,91,115,.42), 0 0 20px rgba(206,91,115,.10)'
    elif next_path:
        border, bg, glow = '#e8b14c', 'linear-gradient(180deg, rgba(232,177,76,.16), rgba(232,177,76,.05))', '0 0 0 1px rgba(232,177,76,.42), 0 0 20px rgba(232,177,76,.10)'
    elif active:
        border, bg, glow = '#7db3ff', 'linear-gradient(180deg, rgba(125,179,255,.18), rgba(125,179,255,.06))', '0 0 0 1px rgba(125,179,255,.45), 0 0 22px rgba(125,179,255,.12)'
    else:
        border, bg, glow = 'rgba(132,149,183,.45)', 'linear-gradient(180deg, rgba(22,30,45,.88), rgba(12,18,29,.96))', 'none'
    ticks = list(tickers or [])[:3]
    tags = ''.join(_tag(t, 'active' if active else ('warn' if next_path else 'neutral')) for t in ticks) or _tag('-', 'neutral')
    title_txt = _safe_text(title)
    label_txt = _safe_text(label)
    summary_txt = _safe_text(summary)
    badge = _tag('YOU ARE HERE', 'active') if active else (_tag('NEXT', 'warn') if next_path else (_tag('RISK', 'bad') if danger else ''))
    return (
        f"<div style='border:1px solid {border};background:{bg};box-shadow:{glow};border-radius:14px;padding:9px 10px;min-height:112px'>"
        f"<div style='display:flex;justify-content:space-between;gap:6px;align-items:flex-start'>"
        f"<div style='font-size:.56rem;color:#9ab0cf;font-weight:800;letter-spacing:.05em;text-transform:uppercase'>{html.escape(title_txt)}</div>"
        f"<div>{badge}</div></div>"
        f"<div style='font-size:.86rem;font-weight:900;line-height:1.06;margin-top:3px'>{html.escape(label_txt)}</div>"
        f"<div style='font-size:.64rem;color:#c6d3e7;line-height:1.16;margin-top:4px'>{html.escape(summary_txt)}</div>"
        f"<div style='font-size:.52rem;color:#8fa5c4;line-height:1.12;margin-top:5px;text-transform:uppercase;letter-spacing:.05em'>Representative tickers</div>"
        f"<div style='margin-top:4px'>{tags}</div>"
        f"</div>"
    )


def _edge(label: str, accent: str = '#7db3ff', dashed: bool = False) -> str:
    line = '1px dashed ' + accent if dashed else '1px solid ' + accent
    return (
        "<div style='display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%'>"
        f"<div style='font-size:.54rem;color:{accent};line-height:1.15;text-align:center;margin-bottom:2px;max-width:86px'>{html.escape(_safe_text(label))}</div>"
        f"<div style='width:18px;border-top:{line};margin-bottom:2px'></div>"
        f"<div style='font-size:1rem;color:{accent};font-weight:900'>→</div></div>"
    )


def _stage_strip(current_stage: str, next_label: str, invalidators: list[str]) -> str:
    stages = [('structural', 'Structural'), ('monthly', 'Monthly'), ('resolved', 'Resolved'), ('spillover', 'Spillover'), ('next', 'Next')]
    items = []
    for key, label in stages:
        tone = 'active' if key == current_stage else ('warn' if key == 'next' else 'neutral')
        items.append(_tag(label, tone))
    inv = ''.join(_tag(x, 'bad') for x in invalidators[:2]) or _tag('-', 'neutral')
    return (
        "<div style='border:1px solid rgba(132,149,183,.32);border-radius:14px;padding:8px 10px;background:rgba(255,255,255,.015);margin:4px 0 8px 0'>"
        f"<div style='font-size:.72rem;font-weight:800;margin-bottom:4px'>Current stage / you are here</div>"
        f"<div style='font-size:.68rem;color:#b7c6dd;margin-bottom:4px'>You are here: <b>{html.escape(_safe_text(current_stage))}</b> · Next watch: <b>{html.escape(_safe_text(next_label))}</b></div>"
        f"<div>{''.join(items)}</div>"
        f"<div style='margin-top:6px;font-size:.62rem;color:#9fb0c8'>Primary invalidators</div><div>{inv}</div>"
        "</div>"
    )


def render_master_rotation_graph(master: dict, title: str = 'Master Correlated Rotation Mind Map') -> None:
    if not master:
        return
    current = str(master.get('current_stage', 'resolved'))
    struct = master.get('structural', {}) or {}
    month = master.get('monthly', {}) or {}
    resolved = master.get('resolved', {}) or {}
    spill = master.get('spillover', {}) or {}
    nxt = master.get('next', {}) or {}
    danger = master.get('danger', {}) or {}
    edges = master.get('edge_labels', {}) or {}
    invalidators = nxt.get('invalidators', []) or []

    st.subheader(title)
    st.caption(f"Active path: {master.get('active_path', '-')} · Next branch watch: {master.get('next_branch_watch', '-')}")
    st.markdown(_stage_strip(current, _safe_text(nxt.get('label', '-')), invalidators), unsafe_allow_html=True)
    html_block = f"""
    <div style='display:grid;grid-template-columns:1fr 34px 1fr 34px 1fr 34px 1fr 34px 1fr 34px 1fr;gap:6px;align-items:stretch;margin-top:2px'>
      <div>{_node('Structural', struct.get('label','-'), struct.get('summary','-'), struct.get('tickers',[]), active=current=='structural')}</div>
      {_edge(edges.get('struct_to_month','-'))}
      <div>{_node('Monthly', month.get('label','-'), month.get('summary','-'), month.get('tickers',[]), active=current=='monthly')}</div>
      {_edge(edges.get('month_to_resolved','-'))}
      <div>{_node('Resolved', resolved.get('label','-'), resolved.get('summary','-'), resolved.get('tickers',[]), active=current=='resolved')}</div>
      {_edge(edges.get('resolved_to_spill','-'))}
      <div>{_node('Spillover', spill.get('label','-'), spill.get('summary','-'), spill.get('tickers',[]), active=current=='spillover')}</div>
      {_edge(edges.get('spill_to_next','-'), accent='#e8b14c', dashed=True)}
      <div>{_node('Next', nxt.get('label','-'), nxt.get('summary','-'), nxt.get('tickers',[]), next_path=True)}</div>
      {_edge(edges.get('next_to_risk','fails if invalidators hit'), accent='#ce5b73', dashed=True)}
      <div>{_node('Risk / invalidator', danger.get('label','-'), danger.get('summary','-'), danger.get('tickers',[]), danger=True)}</div>
    </div>
    """
    st.markdown(html_block, unsafe_allow_html=True)

    b1, b2, b3, b4 = st.columns(4, gap='small')
    branches = master.get('branches', {}) or {}
    order = [('us', 'US'), ('ihsg', 'IHSG/EM'), ('fx', 'FX'), ('commodities', 'Commodities'), ('crypto', 'Crypto')]
    cols = [b1, b2, b3, b4]
    for idx, (key, label) in enumerate(order):
        col = cols[idx % 4]
        br = branches.get(key, {}) or {}
        with col:
            st.markdown(_node(label, br.get('resolved_role', '-'), br.get('summary', '-'), br.get('top_tickers', []), active=False), unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3, gap='small')
    with c1:
        em = master.get('em_rotation', {}) or {}
        st.markdown(_node('EM / IHSG branch', em.get('state', '-'), em.get('summary', '-'), em.get('tickers', ['IHSG','USDIDR','coal']), active=False), unsafe_allow_html=True)
    with c2:
        pd = master.get('petrodollar', {}) or {}
        st.markdown(_node('Oil → shipping → FX/EM', pd.get('state', '-'), pd.get('summary', '-'), pd.get('tickers', ['WTI','NAT','DXY']), next_path=True), unsafe_allow_html=True)
    with c3:
        st.markdown(_node('Invalidators', ', '.join(invalidators[:2]) or '-', danger.get('summary', '-'), danger.get('tickers', []), danger=True), unsafe_allow_html=True)


def render_market_branch_graph(master: dict, market_key: str, title: str = 'Market branch from master map') -> None:
    branch = (master or {}).get('branches', {}).get(market_key, {}) or {}
    if not branch:
        return
    struct_edge = branch.get('edges', {}).get('struct_to_month', 'sets backdrop')
    month_edge = branch.get('edges', {}).get('month_to_resolved', 'narrows route')
    res_edge = branch.get('edges', {}).get('resolved_to_receivers', 'hands off to receivers')
    next_edge = branch.get('edges', {}).get('receivers_to_next', 'next if confirmed')
    st.subheader(title)
    st.caption(f"You are here: {branch.get('current_stage_label', branch.get('resolved_role', '-'))} · Active path: {branch.get('active_path', '-')}")
    st.markdown(_stage_strip(branch.get('current_stage', 'resolved'), branch.get('next_route', '-'), branch.get('invalidators', [])), unsafe_allow_html=True)
    html_block = f"""
    <div style='display:grid;grid-template-columns:1fr 28px 1fr 28px 1fr 28px 1fr 28px 1fr 28px 1fr;gap:6px;align-items:stretch'>
      <div>{_node('Structural', branch.get('structural_role','-'), branch.get('structural_summary','backbone'), branch.get('structural_tickers', branch.get('top_tickers',[])))}</div>
      {_edge(struct_edge)}
      <div>{_node('Monthly', branch.get('monthly_role','-'), branch.get('monthly_summary','overlay'), branch.get('monthly_tickers', branch.get('top_tickers',[])), active=branch.get('current_stage')=='monthly')}</div>
      {_edge(month_edge)}
      <div>{_node('Resolved', branch.get('resolved_role','-'), branch.get('resolved_summary', branch.get('summary','-')), branch.get('resolved_tickers', branch.get('top_tickers',[])), active=branch.get('current_stage','resolved')=='resolved')}</div>
      {_edge(res_edge)}
      <div>{_node('Receivers', branch.get('receiver_label','-'), branch.get('receiver_summary','top live receivers'), branch.get('receiver_tickers', branch.get('top_tickers',[])))}</div>
      {_edge(next_edge, accent='#e8b14c', dashed=True)}
      <div>{_node('Next', branch.get('next_route','-'), branch.get('next_summary','branch to watch'), branch.get('next_tickers', branch.get('risk_tickers',[])), next_path=True)}</div>
      {_edge('fails if invalidator hits', accent='#ce5b73', dashed=True)}
      <div>{_node('Invalidator', ', '.join((branch.get('invalidators') or [])[:2]) or '-', branch.get('invalidator_summary','watch the risk route'), branch.get('risk_tickers',[]), danger=True)}</div>
    </div>
    """
    st.markdown(html_block, unsafe_allow_html=True)
