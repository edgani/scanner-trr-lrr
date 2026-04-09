from __future__ import annotations
from typing import Dict
from utils.math_utils import clamp01


class MarketHealthEngine:
    def run(self, market: Dict[str, float], calibration: Dict[str, object] | None = None) -> Dict[str, object]:
        cal = calibration or {}
        w = cal.get('effective_market_health_weights', {}) if isinstance(cal, dict) else {}
        sector_w = float(w.get('sector', 0.40))
        eqw_w = float(w.get('eqw', 0.25))
        small_w = float(w.get('smallcap', 0.20))
        narrow_w = float(w.get('narrow', 0.25))
        threshold = float((cal or {}).get('market_health_threshold', 0.44))

        sector_ratio = float(market.get('sector_support_ratio', 0.0))
        eqw = float(market.get('eqw_health', 0.5))
        small = float(market.get('smallcap_health', 0.5))
        narrow = float(market.get('narrow_leadership', 0.5))
        breadth = float(market.get('breadth_health', 0.5))
        qqq_rel = float(market.get('qqq_1m', 0.0) - market.get('spy_1m', 0.0))
        contributor_concentration = clamp01(0.5 + qqq_rel / 0.06)
        spider = clamp01(0.30 * max(0.0, float(market.get('vix_1m', 0.0)) / 0.15) + 0.35 * narrow + 0.20 * max(0.0, -float(market.get('iwm_rel_1m', 0.0)) / 0.08) + 0.15 * (1.0 - sector_ratio))

        raw = sector_w * sector_ratio + eqw_w * eqw + small_w * small + 0.10 * breadth - narrow_w * narrow - 0.10 * contributor_concentration + 0.10
        score = clamp01(raw)
        if score >= max(0.68, threshold + 0.18):
            verdict = 'Healthy'
        elif score >= max(0.52, threshold + 0.08):
            verdict = 'Improving'
        elif score >= threshold:
            verdict = 'Narrow'
        else:
            verdict = 'Fragile'

        notes = []
        if sector_ratio < 0.45:
            notes.append('Sedikit sektor yang menopang index')
        if eqw < 0.45:
            notes.append('Equal-weight belum ikut confirm')
        if small < 0.45:
            notes.append('Small caps belum sehat')
        if contributor_concentration > 0.60:
            notes.append('Index terlalu ditopang leader besar')
        if spider > 0.62:
            notes.append('Stress map mulai menyebar')
        if not notes:
            notes.append('Breadth cukup sehat dan leadership lebih merata')

        return {
            'score': score,
            'verdict': verdict,
            'threshold': threshold,
            'sector_support': int(market.get('sector_support_1m', 0.0)),
            'sector_support_3m': int(market.get('sector_support_3m', 0.0)),
            'eqw_confirm': eqw >= 0.50,
            'smallcap_confirm': small >= 0.50,
            'contributor_concentration': contributor_concentration,
            'stress_map': 'Spider web / menyebar' if spider > 0.62 else ('Naik tapi belum sistemik' if spider > 0.42 else 'Masih lokal'),
            'notes': notes,
            'what_confirms': 'Equal-weight, small caps, dan sektor pendukung ikut membaik bersama.',
            'what_invalidates': 'Index naik tapi semakin ditopang sedikit nama / sedikit sektor.',
        }
