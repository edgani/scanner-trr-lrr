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

        oil_market = max(0.0, float(macro.get('oil_3m', 0.0)))
        usd_market = max(0.0, float(market.get('dxy_1m', 0.0)))
        breadth_stress = max(0.0, -float(market.get('rsp_rel_1m', 0.0)))
        smallcap_stress = max(0.0, -float(market.get('iwm_rel_1m', 0.0)))
        long_end = max(0.0, -float(market.get('tlt_1m', 0.0)))

        war_oil_hazard = clamp01(0.16 * escalation + 0.12 * oil_news + 0.28 * oil_market + 0.10 * usd_market + 0.10 * breadth_stress)
        policy_pressure_hazard = clamp01(0.12 * escalation + 0.12 * rates_news + 0.28 * long_end + 0.18 * smallcap_stress + 0.08 * usd_news)
        relief_hazard = clamp01(0.20 * relief + 0.12 * max(0.0, -oil_market) + 0.10 * max(0.0, -usd_market))

        dominant = 'quiet'
        if war_oil_hazard >= max(policy_pressure_hazard, relief_hazard, 0.40):
            dominant = 'war_oil'
        elif policy_pressure_hazard >= max(war_oil_hazard, relief_hazard, 0.36):
            dominant = 'policy_pressure'
        elif relief_hazard >= max(war_oil_hazard, policy_pressure_hazard, 0.25):
            dominant = 'relief'
        elif state in {'active', 'escalating', 'de_escalating'}:
            dominant = state

        display = {
            'war_oil': 'War / oil',
            'policy_pressure': 'Policy pressure',
            'relief': 'Relief',
            'active': 'Active',
            'escalating': 'Escalating',
            'de_escalating': 'De-escalating',
            'quiet': 'Quiet',
        }.get(dominant, 'Quiet')
        confirmation = {
            'oil_confirms': oil_market > 0.08,
            'usd_confirms': usd_market > 0.01,
            'breadth_confirms_stress': breadth_stress > 0.02 or smallcap_stress > 0.03,
            'rates_confirms_pressure': long_end > 0.03,
        }
        summary = 'No major news impulse yet.' if display == 'Quiet' else f'{display} bias with market confirmation check active.'
        return {
            'state': dominant,
            'display_state': display,
            'summary': summary,
            'war_oil_hazard': war_oil_hazard,
            'policy_pressure_hazard': policy_pressure_hazard,
            'relief_hazard': relief_hazard,
            'confirmation': confirmation,
            'headlines': (news or {}).get('top_headlines', []),
        }
