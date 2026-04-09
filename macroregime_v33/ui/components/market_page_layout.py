from __future__ import annotations

import streamlit as st

from ui.components.macro_impact_board import render_macro_impact_board
from ui.components.transmission_panel import render_transmission_panel
from ui.components.checklist_panel import render_checklist_panel
from ui.components.strong_weak_map import render_strong_weak_map
from ui.components.execution_map_panel import render_execution_map_panel
from ui.components.rotation_flow_panel import render_rotation_flow_panel
from ui.components.rotation_flow_logic import build_market_rotation_flows
from ui.components.master_rotation_graph import render_market_branch_graph
from ui.components.current_setups_panel import render_current_setups_panel
from ui.components.forward_radar_panel import render_forward_radar_panel
from ui.components.score_explain_panel import render_score_explain_panel
from ui.components.opportunity_table import render_opportunity_table
from utils.streamlit_utils import info_card, metric_card, render_pills


def _group_by_kind(flows: list[dict]) -> dict[str, list[dict]]:
    out = {
        'rotation_structural': [], 'rotation_monthly': [], 'rotation_resolved': [],
        'spillover_structural': [], 'spillover_monthly': [], 'spillover_resolved': [],
    }
    for flow in flows:
        out.setdefault(str(flow.get('kind', 'rotation_resolved')), []).append(flow)
    return out


def _section_regime_meta(section: dict) -> dict:
    macro = section.get('macro_vs_market', {}) or {}
    hub = section.get('market_hub', {}) or {}
    structural = str(hub.get('structural_quad', macro.get('structural_quad', '-')))
    monthly = str(hub.get('monthly_quad', macro.get('monthly_quad', structural)))
    operating = str(hub.get('operating_regime', macro.get('operating_regime', f"Monthly {monthly} inside Structural {structural}" if monthly != structural else f"Aligned {structural}")))
    dominant = str(hub.get('dominant_horizon', 'aligned'))
    structural_score = hub.get('structural_score', None)
    monthly_score = hub.get('monthly_score', None)
    em_state = str(hub.get('resolved_em_rotation', hub.get('em_rotation', '-')))
    return {
        'structural': structural, 'monthly': monthly, 'operating': operating,
        'resolved_language': str(section.get('macro_vs_market', {}).get('resolved_language', hub.get('resolved_language', operating))),
        'dominant': dominant, 'structural_score': structural_score, 'monthly_score': monthly_score, 'em_state': em_state,
    }


def _render_regime_summary(section: dict) -> None:
    meta = _section_regime_meta(section)
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1.5, 1, 1], gap='small')
    with c1: metric_card('Structural', meta['structural'], 'backbone')
    with c2: metric_card('Monthly', meta['monthly'], 'overlay')
    with c3: metric_card('Operating', meta.get('resolved_language', meta['operating']), 'used now')
    with c4: metric_card('Dominant', meta['dominant'], f"EM {meta['em_state']}")
    conf_band = str(section.get('market_hub', {}).get('confidence_band', '-'))
    with c5: metric_card('Scores', f"S {float(meta['structural_score'] or 0.0):.2f} · M {float(meta['monthly_score'] or 0.0):.2f}", conf_band)
    render_pills([(f"Struct {meta['structural']}", 'blue'), (f"Month {meta['monthly']}", 'warn' if meta['monthly'] != meta['structural'] else 'good'), (f"EM {meta['em_state']}", 'blue')])


def _render_breadth_card(section: dict) -> None:
    snap = (section.get('market_hub', {}) or {})
    lines = [
        f"State: {snap.get('breadth_state', snap.get('breadth_notes', '-'))}",
        f"Trend: {snap.get('breadth_trend', '-')}",
        f"Score: {float(snap.get('breadth_score', 0.0) or 0.0):.2f}",
        f"Sector support: {float(snap.get('sector_support_ratio', 0.0) or 0.0):.2f}",
        f"Narrow leadership: {float(snap.get('narrow_leadership', 0.0) or 0.0):.2f}",
    ]
    info_card('Breadth / Leadership', lines, accent='#365b46')


def _render_hub_card(hub_title: str, hub: dict) -> None:
    rows = []
    for key, value in (hub or {}).items():
        if key in {'strong_list', 'weak_list', 'resolved_language'}:
            continue
        if isinstance(value, dict):
            top = list(value.items())[:3]
            rows.append(key + ': ' + ', '.join(f"{k} {v:.2f}" if isinstance(v, (int, float)) else f"{k} {v}" for k, v in top))
        else:
            rows.append(f"{key}: {value}")
    if rows:
        info_card(hub_title, rows[:5], accent='#28425f')


def _catalyst_lines(section: dict) -> list[str]:
    cat = section.get('catalyst_overlay', {}) or {}
    if not cat:
        return []
    lines = [
        f"Theme: {cat.get('title', '-')}",
        f"State: {cat.get('state', '-')}",
        f"Why: {cat.get('why', '-')}",
    ]
    beneficiaries = ', '.join(cat.get('beneficiaries', [])[:4])
    if beneficiaries:
        lines.append(f"Beneficiaries: {beneficiaries}")
    watch = ', '.join(cat.get('watch', [])[:4])
    if watch:
        lines.append(f"Watch: {watch}")
    lines.append(f"Trigger: {cat.get('trigger', '-')}")
    lines.append(f"Invalidator: {cat.get('invalidator', '-')}")
    return lines




def _render_route_context(section: dict) -> None:
    branch = section.get('route_branch', {}) or {}
    if not branch:
        return
    info_card('What the active route means here', [
        str(branch.get('summary', '-')),
        f"Interpretation: {branch.get('route_interpretation', '-')}",
        f"Winners: {', '.join((branch.get('winners') or [])[:4]) or '-'}",
        f"Losers: {', '.join((branch.get('losers') or [])[:4]) or '-'}",
        f"EM rotation: {branch.get('em_rotation_state', '-')}",
        f"Split: {branch.get('exporter_importer_split', '-')}",
    ], accent='#365b46')

def _render_next_flow(section: dict) -> None:
    nxt = section.get('next_path', {}) or {}
    struct_cands = ', '.join(f"{x.get('quad')} {100*float(x.get('prob',0.0)):.0f}%" for x in (nxt.get('structural_candidates', []) or [])[:2]) or '-'
    month_cands = ', '.join(f"{x.get('quad')} {100*float(x.get('prob',0.0)):.0f}%" for x in (nxt.get('monthly_candidates', []) or [])[:2]) or '-'
    lines = [
        f"Next structural: {nxt.get('next_structural_quad', '-')}",
        f"Struct cands: {struct_cands}",
        f"Next monthly: {nxt.get('next_monthly_quad', '-')}",
        f"Month cands: {month_cands}",
        f"Resolved next: {nxt.get('next_resolved_regime', '-')}",
        f"Flip hazard: {100*float(nxt.get('flip_hazard', 0.0)):.0f}%",
    ]
    lines += [f"Trigger: {x}" for x in (nxt.get('triggers', []) or [])[:2]]
    lines += [f"Invalidate: {x}" for x in (nxt.get('invalidators', []) or [])[:1]]
    info_card('Next Flow / If-Then', lines, accent='#5d4b3b')


def render_market_page(*, title: str, section: dict, checklist_title: str, hub_title: str, master_graph: dict | None = None, market_key: str | None = None) -> None:
    st.title(title)
    flows = build_market_rotation_flows(title, section)
    grouped = _group_by_kind(flows)
    _render_regime_summary(section)

    top_live = section.get('top_opportunities_now', []) or []
    top_next = section.get('top_opportunities_next', []) or []

    live_col, next_col = st.columns(2, gap='small')
    extra_cols = ['ticker','bias','horizon','entry_zone','target','countdown_days_left','review_state','next_action','route_source_label','ev_score']
    if title == 'IHSG':
        extra_cols = extra_cols + ['microstructure_flag']
    with live_col:
        render_opportunity_table(top_live[:6], 'Top opportunities now', cols=extra_cols, empty_msg='Belum ada top opportunities live untuk market ini.')
    with next_col:
        render_opportunity_table(top_next[:6], 'Next opportunities', cols=extra_cols, empty_msg='Belum ada next opportunities untuk market ini.')

    top_l, top_r = st.columns([1.05, 0.95], gap='small')
    with top_l:
        render_macro_impact_board(section.get('macro_vs_market', {}), show_lists=False, show_catalyst=False)
    with top_r:
        render_execution_map_panel(section.get('execution', {}))
        _render_breadth_card(section)

    if master_graph and market_key:
        render_market_branch_graph(master_graph, market_key, title='Branch from Master Correlated Rotation Map')

    d1, d2, d3, d4 = st.columns([1, 1, 1, 1], gap='small')
    with d1:
        _render_route_context(section)
        _render_next_flow(section)
        br = (master_graph or {}).get('branches', {}).get(market_key or '', {}) or {}
        info_card('Current Stage', [f"You are here: {br.get('current_stage_label', '-')}", f"Active path: {br.get('active_path', '-')}", f"Live names: {', '.join((br.get('resolved_tickers') or [])[:3]) or '-'}", f"Next watch names: {', '.join((br.get('next_tickers') or [])[:3]) or '-'}"], accent='#365b46')
    with d2:
        render_checklist_panel(section.get('asset_checklist', [])[:5], title=checklist_title)
    with d3:
        render_strong_weak_map(section.get('strong_weak', {}))
    with d4:
        render_transmission_panel(section.get('transmission', {}))

    _render_hub_card(hub_title, section.get('market_hub', {}) or {})

    with st.expander('Open setup / radar detail blocks', expanded=False):
        s1, s2 = st.columns(2, gap='small')
        with s1:
            render_current_setups_panel(section.get('setups_now', []) or [], title='Setup Sekarang')
        with s2:
            render_forward_radar_panel(section.get('forward_radar', []) or [], title='Forward-Looking')
        cov = section.get('market_hub', {}).get('coverage_report', {}) or {}
        score_notes = [
            f"Score market: {float(section.get('macro_vs_market', {}).get('score', 0.0) or 0.0):.2f}",
            f"Ranking universe aktif: {int(section.get('market_hub', {}).get('ranking_universe_size', 0) or 0)}",
            f"Bucket universe inti: {int(section.get('market_hub', {}).get('bucket_universe_size', 0) or 0)}",
            f"Unbucketed backend names: {len(cov.get('unbucketed_symbols', []) or [])}",
            f"Execution mode: {section.get('execution', {}).get('mode', '-')}",
        ]
        render_score_explain_panel('Score / Routing Snapshot', float(section.get('macro_vs_market', {}).get('score', 0.0) or 0.0), score_notes)

    with st.expander('Open supporting detail blocks', expanded=False):
        cat_lines = _catalyst_lines(section)
        if cat_lines:
            info_card('Catalyst / Theme Overlay', cat_lines[:6], accent='#5d4b3b')
        a, b = st.columns(2, gap='small')
        with a:
            if grouped['rotation_structural']:
                render_rotation_flow_panel(grouped['rotation_structural'], title='Structural Rotation')
            if grouped['rotation_monthly']:
                render_rotation_flow_panel(grouped['rotation_monthly'], title='Monthly Rotation')
            if grouped['rotation_resolved']:
                render_rotation_flow_panel(grouped['rotation_resolved'], title='Resolved Execution')
        with b:
            if grouped['spillover_structural']:
                render_rotation_flow_panel(grouped['spillover_structural'], title='Structural Spillover')
            if grouped['spillover_monthly']:
                render_rotation_flow_panel(grouped['spillover_monthly'], title='Monthly Trigger')
            if grouped['spillover_resolved']:
                render_rotation_flow_panel(grouped['spillover_resolved'], title='Resolved Spillover')
