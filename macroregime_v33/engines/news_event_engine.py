from __future__ import annotations
from typing import Dict
from utils.math_utils import clamp01


class NewsEventEngine:
    def run(self, news: Dict[str, object], market: Dict[str, float], macro: Dict[str, float]) -> Dict[str, object]:
        counts = (news or {}).get('counts', {}) or {}
        state = str((news or {}).get('state', 'quiet'))
        escalation = float(counts.get('escalation', 0.0))
        relief = float(counts.get('relief', 0.0))
        oil_news = float(counts.get('oil', 0.0))
        rates_news = float(counts.get('rates', 0.0))
        usd_news = float(counts.get('usd', 0.0))

        oil_move = float(macro.get('oil_3m', 0.0) or 0.0)
        usd_move = float(market.get('dxy_1m', 0.0) or 0.0)
        breadth_rel = float(market.get('rsp_rel_1m', 0.0) or 0.0)
        smallcap_rel = float(market.get('iwm_rel_1m', 0.0) or 0.0)
        vix_move = float(market.get('vix_1m', 0.0) or 0.0)
        long_end = max(0.0, -float(market.get('tlt_1m', 0.0) or 0.0))

        oil_up = max(0.0, oil_move)
        oil_down = max(0.0, -oil_move)
        usd_up = max(0.0, usd_move)
        usd_down = max(0.0, -usd_move)
        breadth_stress = max(0.0, -breadth_rel)
        smallcap_stress = max(0.0, -smallcap_rel)
        breadth_relief = max(0.0, breadth_rel)
        smallcap_relief = max(0.0, smallcap_rel)
        vol_stress = max(0.0, vix_move)

        war_oil_hazard = clamp01(
            0.15 * escalation
            + 0.10 * oil_news
            + 0.24 * clamp01(0.5 + oil_up / 0.12)
            + 0.10 * clamp01(0.5 + usd_up / 0.04)
            + 0.12 * clamp01(0.5 + breadth_stress / 0.03)
            + 0.08 * clamp01(0.5 + vol_stress / 0.12)
        )
        policy_pressure_hazard = clamp01(
            0.10 * escalation
            + 0.14 * rates_news
            + 0.24 * clamp01(0.5 + long_end / 0.05)
            + 0.16 * clamp01(0.5 + smallcap_stress / 0.04)
            + 0.10 * clamp01(0.5 + usd_up / 0.04)
            + 0.08 * usd_news
        )
        relief_hazard = clamp01(
            0.24 * relief
            + 0.18 * clamp01(0.5 + oil_down / 0.12)
            + 0.10 * clamp01(0.5 + usd_down / 0.04)
            + 0.10 * clamp01(0.5 + breadth_relief / 0.03)
            + 0.08 * clamp01(0.5 + smallcap_relief / 0.04)
        )

        deescalation_watch = clamp01(
            0.55 * relief_hazard
            + 0.15 * relief
            + 0.15 * clamp01(0.5 + oil_down / 0.10)
            + 0.15 * clamp01(0.5 + usd_down / 0.04)
        )
        deescalation_confirmed = clamp01(
            0.35 * deescalation_watch
            + 0.25 * (1.0 if oil_move <= -0.04 else 0.0)
            + 0.15 * (1.0 if breadth_rel >= 0.01 else 0.0)
            + 0.15 * (1.0 if smallcap_rel >= 0.01 else 0.0)
            + 0.10 * (1.0 if usd_move <= 0.00 else 0.0)
        )
        oil_shock_live = clamp01(
            0.45 * war_oil_hazard
            + 0.20 * (1.0 if oil_move >= 0.08 else 0.0)
            + 0.15 * (1.0 if usd_move >= 0.01 else 0.0)
            + 0.10 * (1.0 if breadth_stress >= 0.02 else 0.0)
            + 0.10 * (1.0 if vix_move >= 0.10 else 0.0)
        )
        oil_shock_fading = clamp01(
            0.40 * war_oil_hazard
            + 0.30 * (1.0 if oil_move <= 0.02 else 0.0)
            + 0.15 * (1.0 if usd_move <= 0.01 else 0.0)
            + 0.15 * (1.0 if breadth_rel >= 0.00 else 0.0)
        )

        dominant = 'quiet'
        if oil_shock_live >= max(policy_pressure_hazard, deescalation_confirmed, deescalation_watch, 0.44):
            dominant = 'war_oil'
        elif policy_pressure_hazard >= max(oil_shock_live, deescalation_confirmed, deescalation_watch, 0.38):
            dominant = 'policy_pressure'
        elif deescalation_confirmed >= max(oil_shock_live, policy_pressure_hazard, 0.42):
            dominant = 'deescalation_confirmed'
        elif deescalation_watch >= max(oil_shock_live, policy_pressure_hazard, 0.30):
            dominant = 'deescalation_watch'
        elif oil_shock_fading >= max(policy_pressure_hazard, 0.34):
            dominant = 'oil_shock_fading'
        elif state in {'active', 'escalating', 'de_escalating'}:
            dominant = state

        display = {
            'war_oil': 'War / oil',
            'policy_pressure': 'Policy pressure',
            'deescalation_watch': 'De-escalation watch',
            'deescalation_confirmed': 'De-escalation confirmed',
            'oil_shock_fading': 'Oil shock fading',
            'relief': 'Relief',
            'active': 'Active',
            'escalating': 'Escalating',
            'de_escalating': 'De-escalating',
            'quiet': 'Quiet',
        }.get(dominant, 'Quiet')

        confirmation = {
            'oil_confirms': oil_move > 0.08,
            'oil_relief_confirms': oil_move < -0.04,
            'usd_confirms': usd_move > 0.01,
            'usd_relief_confirms': usd_move <= 0.00,
            'breadth_confirms_stress': breadth_stress > 0.02 or smallcap_stress > 0.03,
            'breadth_confirms_relief': breadth_rel >= 0.01 or smallcap_rel >= 0.01,
            'rates_confirms_pressure': long_end > 0.03,
        }

        if display == 'Quiet':
            summary = 'No major news impulse yet.'
        elif dominant == 'deescalation_confirmed':
            summary = 'De-escalation path has both headline and market confirmation.'
        elif dominant == 'deescalation_watch':
            summary = 'Relief headlines are building, but full market confirmation is not complete yet.'
        elif dominant == 'oil_shock_fading':
            summary = 'Prior oil/geopolitical shock is fading, but not fully cleared.'
        else:
            summary = f'{display} bias with market confirmation check active.'

        return {
            'state': dominant,
            'display_state': display,
            'summary': summary,
            'war_oil_hazard': war_oil_hazard,
            'policy_pressure_hazard': policy_pressure_hazard,
            'relief_hazard': relief_hazard,
            'deescalation_watch': deescalation_watch,
            'deescalation_confirmed': deescalation_confirmed,
            'oil_shock_live': oil_shock_live,
            'oil_shock_fading': oil_shock_fading,
            'confirmation': confirmation,
            'headlines': (news or {}).get('top_headlines', []),
        }
