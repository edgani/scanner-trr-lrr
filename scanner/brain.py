from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_MACRO_FILE = ROOT.parent / 'macroregime_v33' / '.cache' / 'latest_snapshot.json'
DEFAULT_SCANNER_BRAIN_FILE = ROOT / 'data' / 'macro' / 'scanner_brain.json'
RAW_MACRO_FILE = Path(os.getenv('SCANNER_MACRO_FILE', str(DEFAULT_RAW_MACRO_FILE)))
SCANNER_BRAIN_FILE = Path(os.getenv('SCANNER_BRAIN_FILE', str(DEFAULT_SCANNER_BRAIN_FILE)))

MARKET_KEY_MAP = {
    'us': 'us',
    'ihsg': 'ihsg',
    'forex': 'fx',
    'fx': 'fx',
    'commodities': 'commodities',
    'crypto': 'crypto',
}


QUAD_MARKET_POLICY: dict[str, dict[str, dict[str, set[str]]]] = {
    'Q1': {
        'us': {
            'supportive': {'quality_growth', 'financials', 'defensives'},
            'next': {'energy', 'cyclical', 'small_beta'},
            'cut': {'precious'},
            'short': set(),
        },
        'ihsg': {
            'supportive': {'banks', 'cyclical', 'telco_defensive'},
            'next': {'metals_energy', 'energy_exporter'},
            'cut': set(),
            'short': set(),
        },
        'forex': {
            'supportive': {'carry_beta', 'commodity_fx'},
            'next': {'usd_major'},
            'cut': {'jpy_safe_haven', 'safe_haven_fx'},
            'short': set(),
        },
        'commodities': {
            'supportive': {'industrial', 'energy'},
            'next': {'precious'},
            'cut': set(),
            'short': set(),
        },
        'crypto': {
            'supportive': {'majors', 'l1l2', 'defi', 'infra'},
            'next': {'high_beta', 'meme_beta'},
            'cut': {'btc_quality'},
            'short': set(),
        },
    },
    'Q2': {
        'us': {
            'supportive': {'energy', 'cyclical', 'small_beta'},
            'next': {'financials', 'quality_growth'},
            'cut': {'defensives'},
            'short': set(),
        },
        'ihsg': {
            'supportive': {'energy_exporter', 'metals_energy', 'banks'},
            'next': {'cyclical'},
            'cut': {'telco_defensive'},
            'short': set(),
        },
        'forex': {
            'supportive': {'commodity_fx', 'carry_beta', 'em_fx'},
            'next': {'usd_major'},
            'cut': {'jpy_safe_haven', 'safe_haven_fx'},
            'short': set(),
        },
        'commodities': {
            'supportive': {'energy', 'industrial'},
            'next': {'precious'},
            'cut': set(),
            'short': set(),
        },
        'crypto': {
            'supportive': {'majors', 'l1l2', 'defi', 'infra', 'high_beta'},
            'next': {'meme_beta'},
            'cut': {'btc_quality'},
            'short': set(),
        },
    },
    'Q3': {
        'us': {
            'supportive': {'energy', 'defensives', 'quality_growth'},
            'next': {'financials'},
            'cut': {'small_beta', 'high_beta', 'consumer_cyc'},
            'short': {'small_beta', 'high_beta'},
        },
        'ihsg': {
            'supportive': {'banks', 'energy_exporter', 'metals_energy'},
            'next': {'telco_defensive'},
            'cut': {'cyclical'},
            'short': {'cyclical'},
        },
        'forex': {
            'supportive': {'usd_major', 'commodity_fx'},
            'next': {'jpy_safe_haven'},
            'cut': {'carry_beta', 'em_fx'},
            'short': {'carry_beta', 'em_fx'},
        },
        'commodities': {
            'supportive': {'energy', 'precious'},
            'next': {'industrial'},
            'cut': set(),
            'short': set(),
        },
        'crypto': {
            'supportive': {'btc_quality', 'majors'},
            'next': {'infra', 'defi'},
            'cut': {'high_beta', 'meme_beta', 'micro_alt'},
            'short': {'high_beta', 'meme_beta'},
        },
    },
    'Q4': {
        'us': {
            'supportive': {'defensives', 'quality_growth', 'energy'},
            'next': {'financials'},
            'cut': {'small_beta', 'high_beta', 'consumer_cyc', 'semis_beta'},
            'short': {'small_beta', 'high_beta'},
        },
        'ihsg': {
            'supportive': {'banks', 'energy_exporter', 'telco_defensive'},
            'next': {'metals_energy'},
            'cut': {'cyclical'},
            'short': {'cyclical'},
        },
        'forex': {
            'supportive': {'usd_major', 'jpy_safe_haven', 'safe_haven_fx'},
            'next': {'commodity_fx'},
            'cut': {'carry_beta', 'em_fx'},
            'short': {'carry_beta', 'em_fx'},
        },
        'commodities': {
            'supportive': {'precious', 'energy'},
            'next': {'industrial'},
            'cut': set(),
            'short': set(),
        },
        'crypto': {
            'supportive': {'btc_quality', 'majors'},
            'next': {'infra'},
            'cut': {'high_beta', 'meme_beta', 'micro_alt', 'defi'},
            'short': {'high_beta', 'meme_beta', 'micro_alt'},
        },
    },
}


ROUTE_TO_BUCKETS: dict[str, dict[str, set[str]]] = {
    'TLT': {
        'us': {'defensives', 'quality_growth'},
        'ihsg': {'banks', 'telco_defensive'},
        'forex': {'usd_major', 'jpy_safe_haven', 'safe_haven_fx'},
        'commodities': {'precious'},
        'crypto': {'btc_quality', 'majors'},
    },
    'USD': {
        'us': {'defensives'},
        'ihsg': {'banks'},
        'forex': {'usd_major', 'jpy_safe_haven', 'safe_haven_fx'},
        'commodities': {'precious'},
        'crypto': {'btc_quality'},
    },
    'XAUUSD': {
        'us': {'defensives', 'energy'},
        'ihsg': {'energy_exporter', 'metals_energy'},
        'forex': {'safe_haven_fx'},
        'commodities': {'precious'},
        'crypto': {'btc_quality'},
    },
    'WTI': {
        'us': {'energy'},
        'ihsg': {'energy_exporter'},
        'forex': {'commodity_fx'},
        'commodities': {'energy'},
        'crypto': {'majors'},
    },
    'IHSG': {
        'ihsg': {'banks', 'energy_exporter', 'metals_energy'},
    },
    'EEM': {
        'ihsg': {'banks', 'cyclical'},
        'forex': {'em_fx', 'commodity_fx'},
    },
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def _market_alias(market: str) -> str:
    market = str(market).lower().strip()
    if market == 'fx':
        return 'forex'
    return market


def _route_overlay(route_name: str, market: str) -> set[str]:
    return set(ROUTE_TO_BUCKETS.get(str(route_name).strip(), {}).get(_market_alias(market), set()))


@dataclass
class MarketBrain:
    market: str
    current_route: str
    next_route: str
    invalidator_route: str
    execution_mode: str
    shock_state: str
    health_state: str
    crash_state: str
    supportive_buckets: set[str]
    next_buckets: set[str]
    cut_buckets: set[str]
    short_buckets: set[str]
    safe_harbor_buckets: set[str]
    beneficiary_buckets: set[str]
    no_chase_default: bool
    short_bounces_only: bool
    no_trade: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            'market': self.market,
            'current_route': self.current_route,
            'next_route': self.next_route,
            'invalidator_route': self.invalidator_route,
            'execution_mode': self.execution_mode,
            'shock_state': self.shock_state,
            'health_state': self.health_state,
            'crash_state': self.crash_state,
            'supportive_buckets': sorted(self.supportive_buckets),
            'next_buckets': sorted(self.next_buckets),
            'cut_buckets': sorted(self.cut_buckets),
            'short_buckets': sorted(self.short_buckets),
            'safe_harbor_buckets': sorted(self.safe_harbor_buckets),
            'beneficiary_buckets': sorted(self.beneficiary_buckets),
            'no_chase_default': self.no_chase_default,
            'short_bounces_only': self.short_bounces_only,
            'no_trade': self.no_trade,
        }


def normalize_raw_macro(raw: dict[str, Any]) -> dict[str, Any]:
    if not raw:
        return {}

    current_quad = str(raw.get('current_quad') or raw.get('status_ribbon', {}).get('current_quad') or 'unknown')
    next_quad = str(raw.get('next_quad') or raw.get('next_path', {}).get('next_structural_quad') or 'unknown')
    status = raw.get('status_ribbon', {}) or {}
    execution = raw.get('execution_mode', {}) or {}
    next_path = raw.get('next_path', {}) or {}
    risk = raw.get('risk_summary', {}) or {}
    health_verdict = str((raw.get('health', {}) or {}).get('verdict') or status.get('health') or 'unknown')
    shock_state = str((raw.get('shock', {}) or {}).get('state') or 'unknown')
    crash_state = str(risk.get('crash_state') or status.get('crash') or 'unknown')
    safe_harbor = str(raw.get('safe_harbor') or status.get('safe_harbor') or '')
    best_beneficiary = str(raw.get('best_beneficiary') or status.get('best_beneficiary') or '')
    flags = execution.get('flags', {}) if isinstance(execution, dict) else {}

    market_brains: dict[str, dict[str, Any]] = {}
    for scanner_market in ['us', 'ihsg', 'forex', 'commodities', 'crypto']:
        macro_market = MARKET_KEY_MAP[scanner_market]
        section = raw.get(macro_market, {}) or {}
        section_execution = section.get('execution', {}) or {}
        route_branch = section.get('route_branch', {}) or {}
        transmission = section.get('transmission', {}) or {}
        catalyst = section.get('catalyst_overlay', {}) or {}
        base_policy = QUAD_MARKET_POLICY.get(current_quad, QUAD_MARKET_POLICY['Q4']).get(scanner_market, {})
        supportive = set(base_policy.get('supportive', set()))
        next_buckets = set(base_policy.get('next', set()))
        cut_buckets = set(base_policy.get('cut', set()))
        short_buckets = set(base_policy.get('short', set()))

        supportive |= _route_overlay(safe_harbor, scanner_market)
        supportive |= _route_overlay(best_beneficiary, scanner_market)
        next_buckets |= _route_overlay(best_beneficiary, scanner_market)

        if health_verdict.lower() in {'fragile', 'weak'} or crash_state.lower() in {'watch', 'warning', 'elevated'}:
            cut_buckets |= {'high_beta', 'small_beta', 'meme_beta', 'micro_alt', 'carry_beta'}
            short_buckets |= {'high_beta', 'small_beta', 'meme_beta'}
        if shock_state.lower() not in {'normal', 'calm'}:
            supportive |= {'precious', 'energy'} if scanner_market == 'commodities' else set()
            cut_buckets |= {'carry_beta', 'em_fx'} if scanner_market == 'forex' else set()

        current_route = str(route_branch.get('route_interpretation') or transmission.get('structural_route') or status.get('resolved_language') or '')
        next_route = str(transmission.get('next_route') or next_path.get('market_routes', {}).get(macro_market) or next_path.get('next_resolved_regime') or '')
        invalidator_route = ' | '.join((route_branch.get('market_invalidators') or next_path.get('invalidators') or [])[:3])
        execution_mode = str(section_execution.get('mode') or execution.get('execute_mode') or execution.get('mode') or 'balanced')
        market_flags = section_execution.get('flags') if isinstance(section_execution.get('flags'), dict) else {}
        all_flags = dict(flags)
        all_flags.update(market_flags)

        market_brain = MarketBrain(
            market=scanner_market,
            current_route=current_route,
            next_route=next_route,
            invalidator_route=invalidator_route,
            execution_mode=execution_mode,
            shock_state=shock_state,
            health_state=health_verdict,
            crash_state=crash_state,
            supportive_buckets=supportive,
            next_buckets=next_buckets,
            cut_buckets=cut_buckets,
            short_buckets=short_buckets,
            safe_harbor_buckets=_route_overlay(safe_harbor, scanner_market),
            beneficiary_buckets=_route_overlay(best_beneficiary, scanner_market),
            no_chase_default=not bool(all_flags.get('can_chase', False)),
            short_bounces_only=bool(all_flags.get('short_bounces_only', False)),
            no_trade=bool(all_flags.get('no_trade', False)),
        )
        market_brains[scanner_market] = market_brain.to_dict()

    return {
        'generated_at': raw.get('generated_at'),
        'source': 'macroregime_v33',
        'current_quad': current_quad,
        'next_quad': next_quad,
        'current_route': str(status.get('resolved_language') or next_path.get('continuation_path') or ''),
        'next_route': str(next_path.get('next_resolved_regime') or ''),
        'invalidator_route': ' | '.join((next_path.get('invalidators') or [])[:3]),
        'execution_mode': {
            'mode': str(execution.get('mode') or 'balanced'),
            'label': str(execution.get('execute_mode') or execution.get('mode') or 'balanced'),
            'score': execution.get('score'),
            'size_multiplier': execution.get('size_multiplier'),
            'flags': execution.get('flags', {}),
            'notes': execution.get('notes', []),
        },
        'shock_state': shock_state,
        'market_health': health_verdict,
        'crash_state': crash_state,
        'safe_harbor': safe_harbor,
        'best_beneficiary': best_beneficiary,
        'market_brains': market_brains,
    }


def load_brain() -> dict[str, Any]:
    payload = _load_json(SCANNER_BRAIN_FILE)
    if payload:
        return payload
    raw = _load_json(RAW_MACRO_FILE)
    return normalize_raw_macro(raw)


def export_brain(source_file: Path | None = None, target_file: Path | None = None) -> dict[str, Any]:
    source_file = source_file or RAW_MACRO_FILE
    target_file = target_file or SCANNER_BRAIN_FILE
    raw = _load_json(source_file)
    payload = normalize_raw_macro(raw)
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return payload


def current_quad(brain: dict[str, Any]) -> str:
    return str(brain.get('current_quad') or 'unknown')


def next_route(brain: dict[str, Any]) -> dict[str, Any]:
    return {'market_routes': {k if k != 'forex' else 'fx': v.get('next_route', '') for k, v in (brain.get('market_brains', {}) or {}).items()}}


def execution_mode(brain: dict[str, Any]) -> str:
    mode = brain.get('execution_mode', {})
    if isinstance(mode, dict):
        return str(mode.get('label') or mode.get('mode') or 'balanced')
    return str(mode or 'balanced')


def crash_state(brain: dict[str, Any]) -> str:
    return str(brain.get('crash_state') or 'unknown')


def market_policy(brain: dict[str, Any], market: str) -> dict[str, Any]:
    market = _market_alias(market)
    out = ((brain.get('market_brains', {}) or {}).get(market) or {}).copy()
    for key in ['supportive_buckets', 'next_buckets', 'cut_buckets', 'short_buckets', 'safe_harbor_buckets', 'beneficiary_buckets']:
        out[key] = set(out.get(key, []) or [])
    return out


# backward-compatible alias used by older builder code
bucket_policy = market_policy
