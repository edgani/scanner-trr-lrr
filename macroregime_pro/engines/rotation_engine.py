from __future__ import annotations
from typing import Dict

from config.weights import ROTATION_ENGINE_WEIGHTS
from utils.math_utils import clamp01


class RotationEngine:
    def _safe_map(self, quad: str) -> Dict[str, float]:
        return {
            'Q1': {'USD': 0.35, 'XAUUSD': 0.30, 'TLT': 0.30, 'Defensives': 0.35},
            'Q2': {'USD': 0.30, 'XAUUSD': 0.35, 'TLT': 0.28, 'Defensives': 0.30},
            'Q3': {'USD': 0.48, 'XAUUSD': 0.70, 'TLT': 0.46, 'Defensives': 0.52},
            'Q4': {'USD': 0.76, 'XAUUSD': 0.58, 'TLT': 0.72, 'Defensives': 0.62},
        }.get(quad, {'USD': 0.5, 'XAUUSD': 0.5, 'TLT': 0.5, 'Defensives': 0.5})

    def _beneficiary_map(self, quad: str) -> Dict[str, float]:
        return {
            'Q1': {'WTI': 0.40, 'EEM': 0.62, 'IHSG': 0.56, 'XAUUSD': 0.42},
            'Q2': {'WTI': 0.58, 'EEM': 0.68, 'IHSG': 0.62, 'XAUUSD': 0.46},
            'Q3': {'WTI': 0.74, 'EEM': 0.44, 'IHSG': 0.58, 'XAUUSD': 0.72},
            'Q4': {'WTI': 0.28, 'EEM': 0.30, 'IHSG': 0.32, 'XAUUSD': 0.62},
        }.get(quad, {'WTI': 0.5, 'EEM': 0.5, 'IHSG': 0.5, 'XAUUSD': 0.5})

    def _rows(self, items, label, structural_quad, monthly_quad, dominant_horizon):
        route_meta = {
            'USD': {'why': 'Kas safety paling bersih saat dollar dan funding stress mendominasi.', 'confirm': 'DXY tetap kuat, breadth tetap lemah.', 'invalidate': 'Breadth melebar dan yields lebih tenang.'},
            'XAUUSD': {'why': 'Hard-asset hedge paling bersih saat inflation pulse naik tapi growth rapuh.', 'confirm': 'Real yields tidak meledak dan breadth belum sembuh.', 'invalidate': 'Rates dan dollar sama-sama naik keras.'},
            'TLT': {'why': 'Duration jadi tempat kabur kalau growth scare menang.', 'confirm': 'Yields mulai adem dan credit tidak memburuk.', 'invalidate': 'Long-end pain lanjut.'},
            'Defensives': {'why': 'Cash-flow defensives lebih bersih saat broad beta belum sehat.', 'confirm': 'Breadth tetap sempit dan quality outperforms.', 'invalidate': 'Equal-weight dan small caps ikut konfirmasi.'},
            'WTI': {'why': 'Shock inflasi / supply masih dominan.', 'confirm': 'Oil impulse bertahan dan de-escalation belum kredibel.', 'invalidate': 'Oil rollback cepat.'},
            'EEM': {'why': 'Broad EM catch-up mulai hidup, bukan cuma selective exporter.', 'confirm': 'EEM > SPY di 1M dan 3M sambil USD adem.', 'invalidate': 'USD re-accelerates.'},
            'IHSG': {'why': 'Selective exporter + bank quality dalam EM.', 'confirm': 'IHSG > SPY dan commodity chain belum pecah.', 'invalidate': 'USD naik lagi dan commodity leadership luntur.'},
        }
        rows = []
        for rank, (route, score) in enumerate(items, start=1):
            meta = route_meta.get(route, route_meta['USD']).copy()
            rows.append({'rank': rank, 'route': route, 'score': round(score, 3), 'kind': label, 'structural_quad': structural_quad, 'monthly_quad': monthly_quad, 'dominant_horizon': dominant_horizon, **meta})
        return rows

    def _build_outlook(self, label: str, quad: str, leaders: list[str], why: str, duration: str) -> Dict[str, object]:
        return {
            'label': label,
            'quad': quad,
            'leaders': leaders,
            'why': why,
            'expected_duration': duration,
            'maturity': 'early' if quad in {'Q1', 'Q2'} else ('mid' if quad == 'Q3' else 'late/defensive'),
        }

    def run(self, market: Dict[str, float], em_rotation: Dict[str, object], regime_stack: Dict[str, object], news_state: Dict[str, object] | None = None) -> Dict[str, object]:
        state = str((news_state or {}).get('state', 'quiet'))
        resolved = (regime_stack or {}).get('resolved', {}) or {}
        structural_quad = (regime_stack or {}).get('structural', {}).get('quad', 'Q?')
        structural_next = (regime_stack or {}).get('structural', {}).get('next_quad', structural_quad)
        monthly_quad = (regime_stack or {}).get('monthly', {}).get('quad', structural_quad)
        monthly_next = (regime_stack or {}).get('monthly', {}).get('next_quad', monthly_quad)
        dominant_horizon = resolved.get('dominant_horizon', 'aligned')
        operating = resolved.get('operating_regime', f'Aligned {structural_quad}' if monthly_quad == structural_quad else f'Monthly {monthly_quad} inside Structural {structural_quad}')

        structural_safe = self._safe_map(structural_quad)
        monthly_beneficiaries = self._beneficiary_map(monthly_quad)
        next_structural_safe = self._safe_map(structural_next)
        next_monthly_beneficiaries = self._beneficiary_map(monthly_next)

        market_safe = {
            'USD': float(market.get('escape_usd', 0.0)),
            'XAUUSD': float(market.get('escape_xauusd', 0.0)),
            'TLT': float(market.get('escape_tlt', 0.0)),
            'Defensives': max(0.0, 0.5 * float(market.get('xlp_rel_1m', 0.0)) + 0.5 * float(market.get('xlv_rel_1m', 0.0))),
        }
        market_beneficiaries = {
            'WTI': float(market.get('escape_wti', 0.0)),
            'EEM': float(market.get('escape_eem', 0.0)),
            'IHSG': float(market.get('escape_ihsg', 0.0)),
            'XAUUSD': float(market.get('escape_xauusd', 0.0)),
        }

        safe_scores = {k: clamp01(ROTATION_ENGINE_WEIGHTS['structural'] * structural_safe[k] + ROTATION_ENGINE_WEIGHTS['monthly'] * clamp01(0.5 + market_safe[k])) for k in structural_safe}
        beneficiary_scores = {k: clamp01(ROTATION_ENGINE_WEIGHTS['structural'] * monthly_beneficiaries[k] + ROTATION_ENGINE_WEIGHTS['monthly'] * clamp01(0.5 + market_beneficiaries[k])) for k in monthly_beneficiaries}
        next_safe_scores = {k: clamp01(ROTATION_ENGINE_WEIGHTS['structural'] * next_structural_safe[k] + ROTATION_ENGINE_WEIGHTS['monthly'] * clamp01(0.5 + market_safe.get(k, 0.0))) for k in next_structural_safe}
        next_beneficiary_scores = {k: clamp01(ROTATION_ENGINE_WEIGHTS['structural'] * next_monthly_beneficiaries[k] + ROTATION_ENGINE_WEIGHTS['monthly'] * clamp01(0.5 + market_beneficiaries.get(k, 0.0))) for k in next_monthly_beneficiaries}

        if state == 'relief':
            safe_scores['USD'] *= 0.90
            safe_scores['TLT'] *= 1.06
            beneficiary_scores['EEM'] *= 1.08
            beneficiary_scores['IHSG'] *= 1.10
        elif state == 'war_oil':
            safe_scores['USD'] *= 1.08
            safe_scores['XAUUSD'] *= 1.10
            beneficiary_scores['WTI'] *= 1.20
            beneficiary_scores['XAUUSD'] *= 1.08
        elif state == 'policy_pressure':
            safe_scores['USD'] *= 1.10
            safe_scores['TLT'] *= 0.92

        safe_top3 = sorted(safe_scores.items(), key=lambda kv: kv[1], reverse=True)[:3]
        beneficiary_top3 = sorted(beneficiary_scores.items(), key=lambda kv: kv[1], reverse=True)[:3]
        next_safe_top3 = sorted(next_safe_scores.items(), key=lambda kv: kv[1], reverse=True)[:3]
        next_beneficiary_top3 = sorted(next_beneficiary_scores.items(), key=lambda kv: kv[1], reverse=True)[:3]

        safe_rows = self._rows(safe_top3, 'Safe harbor', structural_quad, monthly_quad, dominant_horizon)
        beneficiary_rows = self._rows(beneficiary_top3, 'Best beneficiary', structural_quad, monthly_quad, dominant_horizon)

        resolved_em_state = str(em_rotation.get('resolved_state', em_rotation.get('state', 'not yet')))
        em_row = {'rank': 99, 'route': 'EM rotation', 'score': float(em_rotation.get('resolved_score', em_rotation.get('score', 0.0))), 'state': resolved_em_state.title(), 'why': em_rotation.get('why', 'EM rotation baca dari EEM, IHSG, breadth AS, dan USD.'), 'confirm': 'EEM > SPY 1M & 3M, USD adem, breadth AS tidak sempit.', 'invalidate': 'USD naik lagi / hanya exporter tertentu yang hidup.'}

        aligned = [x['route'] for x in beneficiary_rows if x['score'] >= 0.58 and monthly_quad in {'Q2', 'Q3'}]
        countertrend = [x['route'] for x in beneficiary_rows if x['score'] < 0.52 or (dominant_horizon == 'structural' and monthly_quad != structural_quad)]
        structural_rotation = self._build_outlook('Structural Rotation', structural_quad, [x['route'] for x in safe_rows], 'Structural quad menentukan backbone winner/defensive hierarchy untuk 1–3 bulan.', '1–3 bulan')
        monthly_rotation = self._build_outlook('Monthly Rotation', monthly_quad, [x['route'] for x in beneficiary_rows], 'Monthly quad menentukan siapa yang bergerak duluan secara taktis bulan ini.', '2–6 minggu')
        if dominant_horizon == 'structural':
            resolved_leaders = [x['route'] for x in safe_rows]
        elif dominant_horizon == 'monthly':
            resolved_leaders = [x['route'] for x in beneficiary_rows]
        else:
            resolved_leaders = list(dict.fromkeys([x['route'] for x in beneficiary_rows] + [x['route'] for x in safe_rows]))[:3]
        resolved_rotation = {
            'label': 'Resolved Rotation',
            'operating_regime': operating,
            'dominant_horizon': dominant_horizon,
            'leaders': resolved_leaders,
            'why': 'Resolved flow menggabungkan backbone structural, trigger monthly, dan confirmation signal.',
            'expected_duration': 'now / execution window',
        }
        next_rotation = {
            'label': 'Next Rotation',
            'structural_next_quad': structural_next,
            'monthly_next_quad': monthly_next,
            'leaders': list(dict.fromkeys([r for r, _ in next_beneficiary_top3] + [r for r, _ in next_safe_top3]))[:4],
            'why': 'Next flow dibentuk dari kandidat next structural quad dan next monthly quad saat ini.',
            'expected_duration': 'next 2–8 minggu',
        }

        return {
            'safe_harbor': safe_rows[0]['route'],
            'safe_harbor_why': safe_rows[0]['why'],
            'best_beneficiary': beneficiary_rows[0]['route'],
            'best_beneficiary_why': beneficiary_rows[0]['why'],
            'safe_harbors': safe_rows,
            'beneficiaries': beneficiary_rows,
            'aligned_leaders': aligned[:3],
            'countertrend_leaders': countertrend[:3],
            'structural_route': [x['route'] for x in safe_rows],
            'monthly_route': [x['route'] for x in beneficiary_rows],
            'em_state_text': em_row['why'],
            'rows': safe_rows + beneficiary_rows + [em_row],
            'structural_rotation': structural_rotation,
            'monthly_rotation': monthly_rotation,
            'resolved_rotation': resolved_rotation,
            'next_rotation': next_rotation,
        }
