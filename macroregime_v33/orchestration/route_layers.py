from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import ceil
import re
from typing import Any

MARKET_LABELS = {
    'us': 'US',
    'ihsg': 'IHSG',
    'fx': 'FX',
    'commodities': 'Commodities',
    'crypto': 'Crypto',
}

BASE_WINDOWS = {
    'Trade': 4,
    'Trend': 28,
    'Tail': 90,
}


def _slug(text: str) -> str:
    text = str(text or '').strip().lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_') or 'na'


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _now_iso(as_of: str | None = None) -> str:
    if as_of:
        return as_of
    return datetime.now(timezone.utc).isoformat()


def _days_left(now: datetime, due: datetime | None) -> int | None:
    if due is None:
        return None
    delta = due - now
    return max(0, int(ceil(delta.total_seconds() / 86400.0)))


def _dominant_family(shared_core: dict) -> str:
    petrodollar = float(shared_core.get('petrodollar', {}).get('score', 0.0) or 0.0)
    em = float(shared_core.get('em_rotation', {}).get('resolved_score', shared_core.get('em_rotation', {}).get('score', 0.0)) or 0.0)
    news_state = str(shared_core.get('news_state', {}).get('display_state', shared_core.get('news_state', {}).get('state', ''))).lower()
    next_path = shared_core.get('next_path', {}) or {}
    operating = str(shared_core.get('resolved_regime', {}).get('operating_regime', '')).lower()

    if petrodollar >= 0.55 or any(k in news_state for k in ['war', 'oil', 'energy']):
        return 'petrodollar'
    if em >= 0.55:
        return 'em_rotation'
    if 'q4' in operating or float(next_path.get('flip_hazard', 0.0) or 0.0) >= 0.70:
        return 'growth_scare'
    return 'reflation'


def _route_nodes_for_family(family: str, shared_core: dict, sections: dict[str, dict]) -> tuple[list[dict], list[dict], str, list[str], list[str], dict[str, list[str]], list[str]]:
    petrodollar = shared_core.get('petrodollar', {}) or {}
    em = shared_core.get('em_rotation', {}) or {}
    next_path = shared_core.get('next_path', {}) or {}
    if family == 'petrodollar':
        nodes = [
            {'node_id': 'n1', 'label': 'War / Oil Shock', 'stage': 'trigger', 'direction': 'up', 'strength': 'strong', 'confidence': 0.80, 'why': 'Conflict / oil risk premium drives the route.', 'attached_markets': ['US', 'IHSG', 'FX', 'Commodities'], 'attached_tickers': [], 'attached_sectors': ['Energy', 'Shipping'], 'is_active': True, 'is_override': False, 'is_invalidator': False},
            {'node_id': 'n2', 'label': 'Oil / Freight Stress', 'stage': 'first_order', 'direction': 'up', 'strength': 'strong', 'confidence': 0.77, 'why': str(petrodollar.get('next_route', 'Oil and freight stress rise.')), 'attached_markets': ['Commodities', 'US', 'IHSG'], 'attached_tickers': ['WTI'], 'attached_sectors': ['Energy', 'Tankers'], 'is_active': True, 'is_override': False, 'is_invalidator': False},
            {'node_id': 'n3', 'label': 'Importer Pain / USD Pressure', 'stage': 'second_order', 'direction': 'up', 'strength': 'moderate', 'confidence': 0.73, 'why': 'Higher import costs and tighter funding pressure importers and EM FX.', 'attached_markets': ['FX', 'IHSG', 'Crypto'], 'attached_tickers': ['USDIDR'], 'attached_sectors': ['Importers', 'EM FX'], 'is_active': True, 'is_override': False, 'is_invalidator': False},
            {'node_id': 'n4', 'label': 'Exporter Winners / Beta Pressure', 'stage': 'expression', 'direction': 'mixed', 'strength': 'moderate', 'confidence': 0.75, 'why': 'Commodity exporters benefit while importers / high beta stay vulnerable.', 'attached_markets': ['IHSG', 'US', 'Crypto'], 'attached_tickers': ['AADI', 'ADRO', 'PTBA', 'XLE'], 'attached_sectors': ['Coal', 'Energy', 'High Beta'], 'is_active': True, 'is_override': False, 'is_invalidator': False},
            {'node_id': 'n5', 'label': 'Breaks If Oil / USD Fade', 'stage': 'confirm_break', 'direction': 'mixed', 'strength': 'moderate', 'confidence': 0.70, 'why': 'The route weakens if oil and USD pressure both cool.', 'attached_markets': ['US', 'IHSG', 'FX', 'Commodities', 'Crypto'], 'attached_tickers': [], 'attached_sectors': [], 'is_active': True, 'is_override': False, 'is_invalidator': True},
        ]
        edges = [
            {'edge_id': 'e1', 'from_node_id': 'n1', 'to_node_id': 'n2', 'causal_label': 'Supply-risk premium lifts oil and freight stress', 'polarity': 'positive', 'confidence': 0.80, 'is_active': True, 'is_override': False, 'is_invalidator': False},
            {'edge_id': 'e2', 'from_node_id': 'n2', 'to_node_id': 'n3', 'causal_label': 'Higher oil hurts importers and pressures FX', 'polarity': 'positive', 'confidence': 0.78, 'is_active': True, 'is_override': False, 'is_invalidator': False},
            {'edge_id': 'e3', 'from_node_id': 'n3', 'to_node_id': 'n4', 'causal_label': 'Importer pain splits winners and losers', 'polarity': 'conditional', 'confidence': 0.73, 'is_active': True, 'is_override': False, 'is_invalidator': False},
            {'edge_id': 'e4', 'from_node_id': 'n3', 'to_node_id': 'n5', 'causal_label': 'Route breaks if USD / oil stress fades', 'polarity': 'conditional', 'confidence': 0.70, 'is_active': True, 'is_override': False, 'is_invalidator': True},
        ]
        summary = 'Petrodollar route active: oil and freight stress support exporters, pressure importers, and tighten USD / EM conditions.'
        confirms = ['Oil leadership holds', 'Exporter branch stays stronger than importers', 'USD pressure does not break down']
        invalidators = list((next_path.get('invalidators', []) or [])[:3]) or ['Oil fades without disruption', 'USD pressure eases materially']
        best_expressions = {
            'US': ['XLE', 'selected shipping / tanker names'],
            'IHSG': ['AADI', 'ADRO', 'PTBA'],
            'FX': ['USDIDR', 'importer-sensitive FX shorts'],
            'Commodities': ['WTI', 'coal-linked exposure', 'XAUUSD watch'],
            'Crypto': ['defensive majors watch', 'high-beta underweight'],
        }
        risk_notes = ['Gold can lag even during war if USD and real yields dominate.', 'Energy leadership can fail if the shock is only headline-driven.']
        return nodes, edges, summary, confirms, invalidators, best_expressions, risk_notes

    if family == 'em_rotation':
        nodes = [
            {'node_id': 'n1', 'label': 'USD Relief / EM Flows', 'stage': 'trigger', 'direction': 'down', 'strength': 'moderate', 'confidence': 0.68, 'why': 'Broad EM catch-up needs calmer USD and better breadth.', 'attached_markets': ['FX', 'IHSG', 'Crypto'], 'attached_tickers': [], 'attached_sectors': ['EM'], 'is_active': True, 'is_override': False, 'is_invalidator': False},
            {'node_id': 'n2', 'label': 'Selective EM Rotation', 'stage': 'first_order', 'direction': 'up', 'strength': 'moderate', 'confidence': 0.66, 'why': str(em.get('next_route', 'Exporters lead before broad EM catch-up.')), 'attached_markets': ['IHSG', 'FX'], 'attached_tickers': ['^JKSE'], 'attached_sectors': ['Exporters', 'Banks'], 'is_active': True, 'is_override': False, 'is_invalidator': False},
            {'node_id': 'n3', 'label': 'Broader Participation', 'stage': 'second_order', 'direction': 'up', 'strength': 'weak', 'confidence': 0.58, 'why': 'Breadth must broaden beyond exporters.', 'attached_markets': ['IHSG', 'FX', 'Crypto'], 'attached_tickers': [], 'attached_sectors': ['Broader EM'], 'is_active': True, 'is_override': False, 'is_invalidator': False},
            {'node_id': 'n4', 'label': 'Catch-Up Winners', 'stage': 'expression', 'direction': 'up', 'strength': 'moderate', 'confidence': 0.62, 'why': 'IHSG / EM beta improves if breadth broadens.', 'attached_markets': ['IHSG', 'FX', 'Crypto'], 'attached_tickers': ['^JKSE'], 'attached_sectors': ['Banks', 'Domestic'], 'is_active': True, 'is_override': False, 'is_invalidator': False},
            {'node_id': 'n5', 'label': 'Breaks If USD Re-Accelerates', 'stage': 'confirm_break', 'direction': 'mixed', 'strength': 'moderate', 'confidence': 0.67, 'why': 'EM catch-up fails if USD pressure returns.', 'attached_markets': ['IHSG', 'FX', 'Crypto'], 'attached_tickers': ['DXY'], 'attached_sectors': ['EM FX'], 'is_active': True, 'is_override': False, 'is_invalidator': True},
        ]
        edges = [
            {'edge_id': 'e1', 'from_node_id': 'n1', 'to_node_id': 'n2', 'causal_label': 'USD relief opens the door for EM rotation', 'polarity': 'positive', 'confidence': 0.67, 'is_active': True, 'is_override': False, 'is_invalidator': False},
            {'edge_id': 'e2', 'from_node_id': 'n2', 'to_node_id': 'n3', 'causal_label': 'Selective leadership must broaden into wider participation', 'polarity': 'positive', 'confidence': 0.60, 'is_active': True, 'is_override': False, 'is_invalidator': False},
            {'edge_id': 'e3', 'from_node_id': 'n3', 'to_node_id': 'n4', 'causal_label': 'Broader participation unlocks catch-up winners', 'polarity': 'positive', 'confidence': 0.58, 'is_active': True, 'is_override': False, 'is_invalidator': False},
            {'edge_id': 'e4', 'from_node_id': 'n1', 'to_node_id': 'n5', 'causal_label': 'A renewed USD squeeze breaks the EM route', 'polarity': 'conditional', 'confidence': 0.67, 'is_active': True, 'is_override': False, 'is_invalidator': True},
        ]
        summary = 'Selective EM rotation is active, but broad EM catch-up still needs calmer USD and wider participation.'
        confirms = ['USD cools', 'EEM / IHSG breadth improves', 'Leadership broadens beyond exporters']
        invalidators = ['USD re-accelerates', 'Only exporters keep working', 'EM breadth rolls over again']
        best_expressions = {
            'US': ['EM-sensitive cyclicals watch'],
            'IHSG': ['banks + domestic catch-up watch', 'exporters still core'],
            'FX': ['selective EM FX longs'],
            'Commodities': ['less defensive skew'],
            'Crypto': ['higher-beta watch if liquidity confirms'],
        }
        risk_notes = ['Selective exporters can keep working even if broad EM catch-up fails.']
        return nodes, edges, summary, confirms, invalidators, best_expressions, risk_notes

    nodes = [
        {'node_id': 'n1', 'label': 'Regime Backdrop', 'stage': 'trigger', 'direction': 'mixed', 'strength': 'moderate', 'confidence': 0.60, 'why': 'Fallback route when no single shock dominates.', 'attached_markets': ['US', 'IHSG', 'FX', 'Commodities', 'Crypto'], 'attached_tickers': [], 'attached_sectors': [], 'is_active': True, 'is_override': False, 'is_invalidator': False},
        {'node_id': 'n2', 'label': 'Rotation / Breadth', 'stage': 'first_order', 'direction': 'mixed', 'strength': 'moderate', 'confidence': 0.58, 'why': 'Leadership and breadth decide if the move broadens or narrows.', 'attached_markets': ['US', 'IHSG', 'Crypto'], 'attached_tickers': [], 'attached_sectors': ['Broad Market'], 'is_active': True, 'is_override': False, 'is_invalidator': False},
        {'node_id': 'n3', 'label': 'Best Expressions', 'stage': 'expression', 'direction': 'mixed', 'strength': 'moderate', 'confidence': 0.58, 'why': 'Use the strongest current leaders until the backdrop changes.', 'attached_markets': ['US', 'IHSG', 'FX', 'Commodities', 'Crypto'], 'attached_tickers': [], 'attached_sectors': [], 'is_active': True, 'is_override': False, 'is_invalidator': False},
    ]
    edges = [
        {'edge_id': 'e1', 'from_node_id': 'n1', 'to_node_id': 'n2', 'causal_label': 'Backdrop shapes breadth and leadership', 'polarity': 'conditional', 'confidence': 0.58, 'is_active': True, 'is_override': False, 'is_invalidator': False},
        {'edge_id': 'e2', 'from_node_id': 'n2', 'to_node_id': 'n3', 'causal_label': 'Leadership picks the best current expressions', 'polarity': 'positive', 'confidence': 0.58, 'is_active': True, 'is_override': False, 'is_invalidator': False},
    ]
    summary = 'Fallback route: use current leaders while watching breadth, USD, and next-path invalidators.'
    confirms = ['Breadth improves', 'Leadership stays stable']
    invalidators = list((next_path.get('invalidators', []) or [])[:3]) or ['Breadth breaks', 'USD spikes']
    best_expressions = {v: [] for v in MARKET_LABELS.values()}
    risk_notes = ['This route is lower conviction than petrodollar or EM rotation.']
    return nodes, edges, summary, confirms, invalidators, best_expressions, risk_notes


def build_master_routes(shared_core: dict, sections: dict[str, dict], master_graph: dict, as_of: str | None = None) -> dict:
    as_of = _now_iso(as_of)
    dominant_family = _dominant_family(shared_core)
    nodes, edges, summary, confirms, invalidators, best_expressions, risk_notes = _route_nodes_for_family(dominant_family, shared_core, sections)
    next_path = shared_core.get('next_path', {}) or {}
    em_rotation = shared_core.get('em_rotation', {}) or {}
    petrodollar = shared_core.get('petrodollar', {}) or {}

    active_route = {
        'path_id': f'route_{dominant_family}_active_001',
        'name': str(master_graph.get('resolved', {}).get('label', summary)),
        'family': dominant_family,
        'summary': summary,
        'nodes': nodes,
        'edges': edges,
        'strength': float(master_graph.get('resolved', {}).get('confidence_band', 'medium') == 'high') * 0.2 + 0.62,
        'confidence': float(shared_core.get('status_ribbon', {}).get('confidence', 0.65) or 0.65),
        'confirmations': confirms,
        'invalidators': invalidators,
        'best_expressions': best_expressions,
        'risk_notes': risk_notes,
    }

    override_route = None
    if dominant_family == 'petrodollar' or float(petrodollar.get('score', 0.0) or 0.0) >= 0.45:
        override_route = {
            'path_id': 'route_override_usd_gold_lag_001',
            'name': 'USD / Real-Yield Override Caps Gold',
            'family': 'usd_squeeze',
            'summary': 'War does not automatically mean gold leadership; strong USD / real-yield pressure can cap gold and keep beta defensive.',
            'nodes': [
                {'node_id': 'o1', 'label': 'USD / Real Yield Dominance', 'stage': 'second_order', 'direction': 'up', 'strength': 'moderate', 'confidence': 0.68, 'why': 'Funding stress and real rates cap gold and high beta.', 'attached_markets': ['FX', 'Commodities', 'Crypto'], 'attached_tickers': ['DXY', 'XAUUSD'], 'attached_sectors': [], 'is_active': True, 'is_override': True, 'is_invalidator': False},
                {'node_id': 'o2', 'label': 'Gold Lag / Beta Compression', 'stage': 'expression', 'direction': 'down', 'strength': 'moderate', 'confidence': 0.65, 'why': 'Gold and beta can lag while the override dominates.', 'attached_markets': ['Commodities', 'Crypto'], 'attached_tickers': ['XAUUSD', 'BTCUSD'], 'attached_sectors': ['Precious Metals', 'Crypto'], 'is_active': True, 'is_override': True, 'is_invalidator': False},
            ],
            'edges': [
                {'edge_id': 'oe1', 'from_node_id': 'o1', 'to_node_id': 'o2', 'causal_label': 'USD squeeze and higher real yields cap gold / beta', 'polarity': 'negative', 'confidence': 0.67, 'is_active': True, 'is_override': True, 'is_invalidator': False}
            ],
            'strength': 0.66,
            'confidence': 0.68,
            'confirmations': ['DXY remains firm', 'Gold fails to reclaim leadership'],
            'invalidators': ['DXY weakens materially', 'Gold reclaims leadership'],
            'best_expressions': {
                'US': ['energy over precious-metal beta'],
                'IHSG': ['exporters over importers'],
                'FX': ['USD strength expressions'],
                'Commodities': ['WTI primary, XAUUSD conditional'],
                'Crypto': ['defensive majors over beta'],
            },
            'risk_notes': ['Override can fade quickly if USD and yields cool.'],
        }

    alternate_routes: list[dict] = []
    if float(em_rotation.get('resolved_score', em_rotation.get('score', 0.0)) or 0.0) >= 0.35:
        alternate_routes.append({
            'path_id': 'route_alt_em_rotation_001',
            'name': 'Broad EM Catch-Up',
            'family': 'em_rotation',
            'summary': 'If USD cools and breadth broadens, selective exporter leadership can widen into broader EM catch-up.',
            'nodes': [],
            'edges': [],
            'strength': float(em_rotation.get('resolved_score', em_rotation.get('score', 0.45)) or 0.45),
            'confidence': 0.58,
            'confirmations': ['EEM / IHSG breadth broadens', 'USD cools', 'More than exporters begin leading'],
            'invalidators': ['USD re-accelerates', 'Only exporters keep working'],
            'best_expressions': {
                'US': ['risk-on cyclicals watch'],
                'IHSG': ['banks + broader local participation'],
                'FX': ['selective EM FX longs'],
                'Commodities': ['less defensive skew'],
                'Crypto': ['higher-beta watch if liquidity confirms'],
            },
            'risk_notes': ['Still secondary unless USD pressure clearly cools.'],
        })

    market_branches: dict[str, dict] = {}
    for mk, sec in sections.items():
        label = MARKET_LABELS.get(mk, mk.upper())
        branch = (master_graph.get('branches', {}) or {}).get(mk, {}) or {}
        market_branches[label] = {
            'market': label,
            'branch_id': f'branch_{mk}_001',
            'summary': branch.get('summary', sec.get('macro_vs_market', {}).get('resolved_language', '-')),
            'route_interpretation': branch.get('resolved_summary', branch.get('summary', '-')),
            'winners': list((branch.get('resolved_tickers') or branch.get('receiver_tickers') or branch.get('structural_tickers') or [])[:5]),
            'losers': list((branch.get('risk_tickers') or [])[:5]),
            'filtered_node_ids': [node.get('node_id') for node in nodes if label in node.get('attached_markets', [])],
            'filtered_edge_ids': [edge.get('edge_id') for edge in edges],
            'market_invalidators': list(branch.get('invalidators', [])[:3]) or list(invalidators[:3]),
            'market_confirmations': list(confirms[:3]),
            'top_route_sources': [active_route['path_id']] + ([alternate_routes[0]['path_id']] if alternate_routes and label in {'IHSG', 'FX'} else []) + ([override_route['path_id']] if override_route else []),
            'em_rotation_state': em_rotation.get('resolved_state', em_rotation.get('state', '-')) if label in {'IHSG', 'FX'} else None,
            'exporter_importer_split': ('Exporters favored, importers under pressure' if label in {'IHSG', 'FX'} and float(petrodollar.get('em_importer_pain', 0.0) or 0.0) >= 0.45 else None),
        }

    return {
        'as_of': as_of,
        'active_route': active_route,
        'override_route': override_route,
        'alternate_routes': alternate_routes,
        'market_branches': market_branches,
        'dominant_family': dominant_family,
        'dominant_summary': active_route['summary'],
        'global_confirmations': confirms,
        'global_invalidators': invalidators,
        'em_rotation_summary': str(em_rotation.get('next_route', 'EM exporters vs importers')),
        'petrodollar_summary': str(petrodollar.get('next_route', 'Oil -> shipping -> importer pain -> FX/EM')),
    }


def _infer_horizon(market_label: str, row: dict, is_radar: bool = False, force_tail: bool = False) -> str:
    if force_tail:
        return 'Tail'
    name = str(row.get('name', ''))
    score = abs(float(row.get('score', 0.0) or 0.0))
    side = str(row.get('side', '')).lower()
    if market_label in {'FX', 'Crypto'}:
        return 'Trade'
    if market_label == 'Commodities' and ('XAU' in name or 'WTI' in name or score >= 0.18):
        return 'Trend'
    if is_radar:
        return 'Trend'
    if market_label in {'US', 'IHSG'} and side == 'long' and score >= 0.18:
        return 'Trend'
    return 'Trend'


def _entry_zone(row: dict, is_radar: bool) -> str:
    explicit = str(row.get('entry_zone', '') or '').strip()
    if explicit:
        return explicit
    action = str(row.get('action', row.get('radar_type', ''))).lower()
    if 'reset' in action or 'retrace' in action:
        return 'pullback / reset zone near support'
    if 'break' in action or 'breakout' in action:
        return 'breakout-retest zone'
    if is_radar:
        return 'wait for trigger / confirmation zone'
    return 'favorable retrace / continuation zone'


def _target_label(horizon: str, bias: str, is_radar: bool, row: dict | None = None) -> str:
    row = row or {}
    explicit = str(row.get('target', row.get('t1_t2', '')) or '').strip()
    if explicit:
        return explicit
    if is_radar:
        return 'activate only after trigger; then target next clean expansion leg'
    if horizon == 'Trade':
        return 'tactical extension / first clean move'
    if horizon == 'Tail':
        return 'structural continuation while thesis stays intact'
    return 'next trend leg / swing extension'


def _macro_aligned(bias: str, is_radar: bool) -> str:
    if is_radar:
        return 'Partial'
    return 'Yes' if bias in {'Long', 'Short'} else 'Partial'


def _confidence_from_score(score: float, is_radar: bool) -> float:
    base = 0.52 + min(abs(score), 0.35) * 1.1
    if is_radar:
        base -= 0.08
    return max(0.35, min(base, 0.92))


def _ev_score(score: float, confidence: float, is_radar: bool, macro_aligned: str, horizon: str) -> float:
    val = abs(score) * 30 + confidence * 5
    if not is_radar:
        val += 1.0
    if macro_aligned == 'Yes':
        val += 0.8
    if horizon == 'Tail':
        val += 0.5
    return round(val, 2)


def _stable_key(row: dict, market_label: str, bias: str, horizon: str, is_radar: bool) -> str:
    return f"{market_label}|{row.get('name','')}|{bias}|{horizon}|{'radar' if is_radar else 'live'}"


def _find_prior_lifecycle(prior_snapshot: dict | None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not isinstance(prior_snapshot, dict):
        return out
    records = (prior_snapshot.get('position_lifecycle') or {}).get('records', []) or []
    for rec in records:
        key = rec.get('signal_key') or f"{rec.get('market')}|{rec.get('ticker')}|{rec.get('bias', rec.get('next_action',''))}|{rec.get('horizon')}|live"
        out[str(key)] = rec
    return out


def build_master_opportunities(sections: dict[str, dict], master_routes: dict, as_of: str | None = None, prior_snapshot: dict | None = None) -> dict:
    as_of = _now_iso(as_of)
    now = _parse_dt(as_of) or datetime.now(timezone.utc)
    prior_lookup = _find_prior_lifecycle(prior_snapshot)
    rows: list[dict] = []
    top_now_by_market: dict[str, list[str]] = {v: [] for v in MARKET_LABELS.values()}
    top_next_by_market: dict[str, list[str]] = {v: [] for v in MARKET_LABELS.values()}

    for mk, sec in sections.items():
        market_label = MARKET_LABELS[mk]
        branch = master_routes.get('market_branches', {}).get(market_label, {}) or {}
        top_sources = list(branch.get('top_route_sources', []))
        default_source_id = top_sources[0] if top_sources else master_routes.get('active_route', {}).get('path_id', '')
        default_source_label = master_routes.get('active_route', {}).get('name', master_routes.get('dominant_summary', '-'))
        branch_summary = branch.get('summary', sec.get('macro_vs_market', {}).get('resolved_language', '-'))

        def add_row(row: dict, is_radar: bool, force_tail: bool = False) -> None:
            side = str(row.get('side', 'watch')).lower()
            bias = {'long': 'Long', 'short': 'Short'}.get(side, 'Watch')
            horizon = _infer_horizon(market_label, row, is_radar=is_radar, force_tail=force_tail)
            key = _stable_key(row, market_label, bias, horizon, is_radar)
            prior = prior_lookup.get(key, {})
            birth_ts = str(prior.get('signal_birth_ts') or as_of)
            birth_dt = _parse_dt(birth_ts) or now
            base_conf = _confidence_from_score(float(row.get('score', 0.0) or 0.0), is_radar=is_radar)
            row_conf = row.get('signal_confidence', None)
            confidence = max(base_conf, float(row_conf)) if isinstance(row_conf, (int, float)) else base_conf
            macro_aligned = _macro_aligned(bias, is_radar)
            base_window = BASE_WINDOWS[horizon]
            if bias == 'Watch' or is_radar:
                base_window = max(3, int(round(base_window * 0.6)))
            if force_tail:
                base_window = BASE_WINDOWS['Tail']
            due_dt = birth_dt + timedelta(days=base_window)
            countdown = _days_left(now, due_dt)
            state = 'Watchlist' if is_radar else 'Actionable'
            review_state = 'Review Due' if countdown is not None and countdown <= 2 and is_radar else ('Healthy' if confidence >= 0.72 else 'Maturing')
            next_action = 'Watch' if is_radar else ('Still Hold' if review_state != 'Review Due' else 'Trim')
            if confidence < 0.58 and not is_radar:
                review_state = 'Maturing'
            route_source_id = default_source_id
            route_source_label = default_source_label
            tags = [market_label, horizon]
            em_state = branch.get('em_rotation_state')
            if em_state and market_label in {'IHSG', 'FX'}:
                tags.append('EM Rotation')
            if 'exporter' in str(branch.get('exporter_importer_split', '')).lower() and bias == 'Long':
                tags.append('Exporter')
            if force_tail:
                tags.append('Tail')
            score = float(row.get('score', 0.0) or 0.0)
            ev_score = _ev_score(score, confidence, is_radar, macro_aligned, horizon)
            micro_flag = str(row.get('microstructure_flag', row.get('structural_flag', '')) or '').strip()
            opp = {
                'opportunity_id': f"opp_{_slug(market_label)}_{_slug(row.get('name',''))}_{bias.lower()}_{horizon.lower()}_{'radar' if is_radar else 'live'}",
                'signal_id': f"sig_{_slug(row.get('name',''))}_{horizon.lower()}_{'radar' if is_radar else 'live'}",
                'signal_key': key,
                'ticker': str(row.get('name', '')).strip(),
                'display_name': str(row.get('name', '')).strip(),
                'market': market_label,
                'asset_class': {'US': 'Equity', 'IHSG': 'Equity', 'FX': 'FX Pair', 'Commodities': 'Commodity', 'Crypto': 'Crypto'}.get(market_label, 'Asset'),
                'bias': bias,
                'horizon': horizon,
                'entry_zone': _entry_zone(row, is_radar),
                'invalidation': str(row.get('invalidator', row.get('not_ready', 'route loses support / breadth fails'))),
                'target': _target_label(horizon, bias, is_radar, row=row),
                'stop_logic': 'review on invalidation or route failure',
                'why_now': str(row.get('why_now', row.get('why_radar', branch_summary))),
                'why_not_yet': str(row.get('why_not_yet', row.get('not_ready', '')) or ''),
                'signal_quality_note': str(row.get('signal_quality', '') or ''),
                't1_t2': str(row.get('t1_t2', '') or ''),
                'route_source_id': route_source_id,
                'route_source_label': route_source_label,
                'macro_aligned': macro_aligned,
                'confidence': round(confidence, 3),
                'ev_score': ev_score,
                'rank_global': 0,
                'rank_within_market': 0,
                'review_state': review_state,
                'next_action': next_action,
                'state': state,
                'countdown_days_left': countdown,
                'review_due_at': due_dt.isoformat(),
                'signal_birth_ts': birth_ts,
                'holding_window_days': base_window,
                'holding_window_label': f"{base_window}D" if base_window < 14 else (f"{round(base_window/7)}W" if base_window < 70 else f"{round(base_window/30)}M"),
                'market_context_summary': branch_summary,
                'market_branch_id': branch.get('branch_id', f'branch_{mk}_001'),
                'relative_strength_note': 'Strong versus peers' if score >= 0 else 'Weak versus peers',
                'breadth_note': str(sec.get('market_hub', {}).get('breadth_state', '-')),
                'liquidity_note': 'Sufficient for featured opportunity list',
                'exhaustion_note': str(row.get('risk', 'Normal')),
                'microstructure_flag': micro_flag,
                'structural_penalty_note': 'Structural fragility penalty active' if micro_flag else '',
                'tags': tags + (['Microstructure'] if micro_flag else []),
                '_raw_score': score,
            }
            rows.append(opp)

        live_rows = sec.get('setups_now', []) or []
        radar_rows = sec.get('forward_radar', []) or []
        for row in live_rows:
            add_row(row, is_radar=False, force_tail=False)
            side = str(row.get('side', '')).lower()
            score = abs(float(row.get('score', 0.0) or 0.0))
            if market_label in {'US', 'IHSG', 'Commodities'} and side == 'long' and score >= 0.18:
                add_row(row, is_radar=False, force_tail=True)
        for row in radar_rows:
            add_row(row, is_radar=True, force_tail=False)

    rows.sort(key=lambda r: (r['state'] != 'Actionable', -float(r['ev_score']), -float(r['confidence']), r['ticker']))
    for idx, row in enumerate(rows, start=1):
        row['rank_global'] = idx

    by_market: dict[str, list[dict]] = {v: [] for v in MARKET_LABELS.values()}
    for row in rows:
        by_market[row['market']].append(row)
    for market_label, market_rows in by_market.items():
        market_rows.sort(key=lambda r: (r['state'] != 'Actionable', -float(r['ev_score']), -float(r['confidence']), r['ticker']))
        for idx, row in enumerate(market_rows, start=1):
            row['rank_within_market'] = idx
        top_now_by_market[market_label] = [r['opportunity_id'] for r in market_rows if r['state'] == 'Actionable'][:8]
        top_next_by_market[market_label] = [r['opportunity_id'] for r in market_rows if r['state'] != 'Actionable'][:8]

    top_global_now = [r['opportunity_id'] for r in rows if r['state'] == 'Actionable'][:12]
    top_global_next = [r['opportunity_id'] for r in rows if r['state'] != 'Actionable'][:12]

    for row in rows:
        row.pop('_raw_score', None)

    return {
        'as_of': as_of,
        'rows': rows,
        'top_now_by_market': top_now_by_market,
        'top_next_by_market': top_next_by_market,
        'top_global_now': top_global_now,
        'top_global_next': top_global_next,
    }


def build_position_lifecycle(master_opportunities: dict, master_routes: dict, as_of: str | None = None, prior_snapshot: dict | None = None) -> dict:
    as_of = _now_iso(as_of)
    now = _parse_dt(as_of) or datetime.now(timezone.utc)
    prior_lookup = _find_prior_lifecycle(prior_snapshot)
    records: list[dict] = []
    due_reviews: list[str] = []
    summary = {'total_records': 0, 'healthy': 0, 'maturing': 0, 'review_due': 0, 'invalidated': 0}

    opp_by_id = {row['opportunity_id']: row for row in master_opportunities.get('rows', [])}
    for row in master_opportunities.get('rows', []):
        key = row.get('signal_key') or _stable_key({'name': row['ticker']}, row['market'], row['bias'], row['horizon'], row['state'] != 'Actionable')
        prior = prior_lookup.get(key, {})
        birth_ts = str(prior.get('signal_birth_ts') or row.get('signal_birth_ts') or as_of)
        birth_dt = _parse_dt(birth_ts) or now
        base_window = int(row.get('holding_window_days', BASE_WINDOWS.get(row.get('horizon', 'Trend'), 28)) or 28)
        adjusted_window = base_window
        if float(row.get('confidence', 0.0) or 0.0) >= 0.80 and row.get('state') == 'Actionable':
            adjusted_window = base_window + max(1, int(round(base_window * 0.10)))
        due_dt = birth_dt + timedelta(days=adjusted_window)
        days_elapsed = max(0, int((now - birth_dt).total_seconds() // 86400))
        countdown = _days_left(now, due_dt)
        route_intact = True
        breadth_ok = str(row.get('breadth_note', '-')).lower() not in {'fragile', 'narrow / fragile'}
        rs_ok = 'weak' not in str(row.get('relative_strength_note', '')).lower()
        review_state = str(row.get('review_state', 'Healthy'))
        next_action = str(row.get('next_action', 'Still Hold'))
        lifecycle_phase = 'Fresh'
        if row.get('state') != 'Actionable':
            lifecycle_phase = 'Review'
        elif countdown is not None and countdown <= 2:
            lifecycle_phase = 'Review'
            review_state = 'Review Due'
            next_action = 'Trim' if row.get('bias') in {'Long', 'Short'} else 'Watch'
        elif days_elapsed >= max(1, int(adjusted_window * 0.66)):
            lifecycle_phase = 'Mature'
        elif days_elapsed >= max(1, int(adjusted_window * 0.33)):
            lifecycle_phase = 'Developing'

        if review_state == 'Review Due':
            due_reviews.append(f"life_{row['opportunity_id']}")
            summary['review_due'] += 1
        elif review_state == 'Healthy':
            summary['healthy'] += 1
        elif review_state in {'Maturing', 'Stretched', 'Fragile'}:
            summary['maturing'] += 1
        elif review_state == 'Invalidated':
            summary['invalidated'] += 1

        record = {
            'lifecycle_id': f"life_{row['opportunity_id']}",
            'opportunity_id': row['opportunity_id'],
            'signal_key': key,
            'ticker': row['ticker'],
            'market': row['market'],
            'bias': row['bias'],
            'horizon': row['horizon'],
            'signal_birth_ts': birth_ts,
            'last_review_ts': as_of,
            'next_review_due_ts': due_dt.isoformat(),
            'base_window_days': base_window,
            'adjusted_window_days': adjusted_window,
            'days_elapsed': days_elapsed,
            'countdown_days_left': countdown,
            'lifecycle_phase': lifecycle_phase,
            'review_state': review_state,
            'next_action': next_action,
            'route_source_id': row['route_source_id'],
            'route_still_intact': route_intact,
            'relative_strength_ok': rs_ok,
            'breadth_ok': breadth_ok,
            'target_progress_pct': min(0.95, round((1.0 - (countdown or 0) / max(adjusted_window, 1)) * 0.8, 2)) if countdown is not None else 0.0,
            'exhaustion_flag': 'high' in str(row.get('exhaustion_note', '')).lower() and row.get('state') == 'Actionable',
            'invalidated_flag': review_state == 'Invalidated',
            'review_history': [{
                'review_ts': as_of,
                'prior_state': review_state,
                'new_state': review_state,
                'decision': next_action,
                'reason': 'Lifecycle review uses route integrity, relative strength, breadth, and countdown expiry.',
                'reviewer_engine': 'position_lifecycle_engine_v1',
            }],
        }
        records.append(record)

        # sync back into master opportunity row
        row['countdown_days_left'] = countdown
        row['review_due_at'] = due_dt.isoformat()
        row['review_state'] = review_state
        row['next_action'] = next_action
        row['signal_birth_ts'] = birth_ts

    summary['total_records'] = len(records)
    return {
        'as_of': as_of,
        'records': records,
        'due_reviews': due_reviews,
        'summary': summary,
    }


def build_home_summary(master_routes: dict, master_opportunities: dict, position_lifecycle: dict, shared_core: dict) -> dict:
    opp_rows = master_opportunities.get('rows', []) or []
    best_long = next((r for r in opp_rows if r.get('bias') == 'Long' and r.get('state') == 'Actionable'), None)
    best_short = next((r for r in opp_rows if r.get('bias') == 'Short' and r.get('state') == 'Actionable'), None)
    best_hedge = next((r for r in opp_rows if r.get('market') in {'FX', 'Commodities'} and r.get('state') == 'Actionable'), None)
    safe_harbor = next((r for r in opp_rows if 'defensive' in ' '.join(r.get('tags', [])).lower()), None) or best_hedge or best_long
    next_macro_summary = shared_core.get('next_macro_summary', {}) or {}
    invalidators = master_routes.get('global_invalidators', []) or []
    due = position_lifecycle.get('due_reviews', []) or []
    strongest = shared_core.get('rotation', {}).get('resolved_rotation', {}).get('leaders', []) or []
    return {
        'dominant_route': master_routes.get('dominant_summary', '-'),
        'dominant_family': master_routes.get('dominant_family', '-'),
        'best_long': best_long,
        'best_short': best_short,
        'best_hedge': best_hedge,
        'safe_harbor': safe_harbor,
        'main_risk': invalidators[0] if invalidators else 'Watch breadth / USD / credit route',
        'next_catalyst': next_macro_summary.get('family', '-') or '-',
        'next_catalyst_countdown': next_macro_summary.get('countdown', '-'),
        'due_reviews': len(due),
        'strongest_markets': strongest[:5],
    }


def build_scenario_lab(shared_core: dict, master_routes: dict) -> dict:
    scenarios = shared_core.get('scenario_family', []) or []
    next_path = shared_core.get('next_path', {}) or {}
    return {
        'active_route_summary': master_routes.get('dominant_summary', '-'),
        'alternate_routes': master_routes.get('alternate_routes', []),
        'switch_triggers': list(next_path.get('triggers', [])[:5]),
        'invalidators': list(master_routes.get('global_invalidators', [])[:5]),
        'next_resolved_regime': next_path.get('next_resolved_regime', '-'),
        'continuation_path': next_path.get('continuation_path', '-'),
        'monthly_fade_path': next_path.get('monthly_fade_path', '-'),
        'structural_flip_path': next_path.get('structural_flip_path', '-'),
        'scenario_family': scenarios,
        'scenario_tab_impact_map': shared_core.get('scenario_tab_impact_map', []),
    }


def attach_market_views(sections: dict[str, dict], master_routes: dict, master_opportunities: dict) -> None:
    rows = master_opportunities.get('rows', []) or []
    by_market: dict[str, list[dict]] = {k: [] for k in sections}
    for row in rows:
        mk = row.get('market')
        for key, label in MARKET_LABELS.items():
            if mk == label:
                by_market[key].append(row)
                break
    for key, sec in sections.items():
        label = MARKET_LABELS[key]
        market_rows = sorted(by_market.get(key, []), key=lambda r: (r.get('state') != 'Actionable', -float(r.get('ev_score', 0.0)), -float(r.get('confidence', 0.0))))
        sec['top_opportunities_now'] = [r for r in market_rows if r.get('state') == 'Actionable'][:8]
        sec['top_opportunities_next'] = [r for r in market_rows if r.get('state') != 'Actionable'][:8]
        sec['route_branch'] = master_routes.get('market_branches', {}).get(label, {}) or {}
