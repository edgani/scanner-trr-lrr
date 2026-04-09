from __future__ import annotations
import json
from pathlib import Path
from config.settings import MACRO_DIR

MARKET_MAP = {'us': 'us', 'ihsg': 'ihsg', 'forex': 'fx', 'commodities': 'commodities', 'crypto': 'crypto'}

def load_macro_snapshot(path: Path | None = None) -> dict:
    path = path or (MACRO_DIR / 'latest_snapshot.json')
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))

def market_macro_overlay(market: str, snapshot: dict | None = None) -> dict:
    snap = snapshot or load_macro_snapshot()
    section = snap.get(MARKET_MAP.get(market, market), {}) if snap else {}
    shared = snap.get('shared_core', {}) if snap else {}
    execution = section.get('execution', {}) if isinstance(section, dict) else {}
    macro_vs = section.get('macro_vs_market', {}) if isinstance(section, dict) else {}
    next_path = section.get('next_path', {}) if isinstance(section, dict) else {}
    crash_state = (shared.get('shock') or {}).get('state', 'mixed') if isinstance(shared.get('shock'), dict) else 'mixed'
    regime = shared.get('resolved_regime') or shared.get('regime') or 'unknown'
    if isinstance(regime, dict):
        regime = regime.get('resolved_language') or regime.get('operating_regime') or str(regime)
    return {
        'backend': 'macro_snapshot' if snap else 'none',
        'regime': str(regime),
        'execution_mode': str(execution.get('mode', 'balanced')),
        'market_bias': str(execution.get('bias', 'mixed')),
        'crash_state': str(crash_state),
        'summary': str(macro_vs.get('now', '') or ''),
        'next_route': str(next_path.get('continuation_path', '') or ''),
        'invalidator_route': str(next_path.get('structural_flip_path', '') or ''),
        'focus': str(macro_vs.get('next_macro_focus', '') or section.get('focus', '') or ''),
        'next_macro_countdown': str(macro_vs.get('next_macro_countdown', '-') or '-'),
        'next_macro_focus': str(macro_vs.get('next_macro_focus', '-') or '-'),
        'best_beneficiary': ', '.join([str(x) for x in (section.get('catalyst_overlay', {}) or {}).get('beneficiaries', [])[:2]]),
    }

def macro_alignment_for_side(side: str, overlay: dict) -> tuple[str, float, str]:
    bias = str(overlay.get('market_bias', '')).lower()
    mode = str(overlay.get('execution_mode', '')).lower()
    crash = str(overlay.get('crash_state', '')).lower()
    summary = str(overlay.get('summary', '') or overlay.get('focus', '') or '').strip()
    score = 0.0
    if any(x in bias for x in ['two-way', 'mixed', 'balanced']) or any(x in mode for x in ['balanced', 'two-way', 'reset']):
        score += 0.25
    if 'normal' in crash:
        score += 0.1
    if side == 'Long':
        if any(x in bias for x in ['bull', 'long', 'supportive', 'up']):
            score += 1.0
        if any(x in mode for x in ['aggressive', 'trend', 'risk_on', 'long']):
            score += 0.6
        if any(x in mode for x in ['defensive', 'risk_off']):
            score -= 0.35
        if any(x in crash for x in ['shock', 'hostile', 'crash']):
            score -= 0.8
    else:
        if any(x in bias for x in ['bear', 'short', 'down', 'hostile', 'weak']):
            score += 1.0
        if any(x in mode for x in ['defensive', 'risk_off', 'short']):
            score += 0.6
        if any(x in mode for x in ['aggressive', 'trend', 'risk_on', 'long']):
            score -= 0.25
        if any(x in crash for x in ['shock', 'hostile', 'crash']):
            score += 0.5
    if score >= 0.9:
        return 'Yes', 1.0, summary or 'Macro sejalan.'
    if score >= 0.1:
        return 'Mixed', 0.8, summary or 'Macro belum ideal tapi tidak melawan keras.'
    return 'No', 0.45, summary or 'Macro tidak sejalan.'

def macro_multiplier(label: str) -> float:
    return {'Yes': 1.0, 'Mixed': 0.85, 'No': 0.5}.get(label, 0.8)
