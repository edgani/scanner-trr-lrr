from __future__ import annotations
from typing import Dict

from config.weights import CRASH_METER_WEIGHTS
from utils.math_utils import clamp01


def _state(x: float) -> str:
    if x >= 0.72:
        return 'elevated'
    if x >= 0.48:
        return 'watch'
    return 'calm'


class CrashMeterEngine:
    def run(
        self,
        weather: Dict[str, object],
        shock: Dict[str, object],
        health: Dict[str, object],
        vix_bucket: Dict[str, object],
        positioning: Dict[str, object],
        derivatives: Dict[str, float],
        market: Dict[str, float],
    ) -> Dict[str, object]:
        tail_state = 1.0 if str(weather.get('tail_state', 'neutral')) == 'stressed' else 0.35 if str(weather.get('tail_state', 'neutral')) == 'neutral' else 0.10
        shock_state = 1.0 if str(shock.get('state', 'normal')) == 'shock' else 0.70 if str(shock.get('state', 'normal')) == 'stress' else 0.35 if str(shock.get('state', 'normal')) == 'watch' else 0.10
        health_fragility = 0.85 if str(health.get('verdict', 'mixed')) == 'Fragile' else 0.65 if str(health.get('verdict', 'mixed')) == 'Narrow' else 0.35 if str(health.get('verdict', 'mixed')) == 'mixed' else 0.15
        vix_state = 0.90 if str(vix_bucket.get('bucket', 'Unknown')) == 'Defensive' else 0.55 if str(vix_bucket.get('bucket', 'Unknown')) == 'Chop' else 0.20
        unwind = clamp01(float(positioning.get('unwind_risk_proxy', positioning.get('unwind_risk', 0.5))))
        vol_stress = clamp01(float(derivatives.get('vol_stress', 0.5)))
        tail_hedge_bid = clamp01(float(derivatives.get('tail_hedge_bid', 0.5)))
        dollar_pressure = clamp01(0.5 + float(market.get('dxy_1m', 0.0)) / 0.04)
        weather_risk = 1.0 - clamp01(float(weather.get('score', 0.5)))

        # Crash = tail / cascade risk. Risk-off = broader defensive deterioration.
        crash_score = clamp01(
            CRASH_METER_WEIGHTS['tail_state'] * tail_state
            + CRASH_METER_WEIGHTS['shock_state'] * shock_state
            + 0.16 * health_fragility
            + 0.10 * vix_state
            + CRASH_METER_WEIGHTS['unwind_risk'] * unwind
            + CRASH_METER_WEIGHTS['vol_stress'] * vol_stress
            + CRASH_METER_WEIGHTS['tail_hedge_bid'] * tail_hedge_bid
            + 0.08 * dollar_pressure
        )
        risk_off_score = clamp01(
            0.30 * weather_risk
            + 0.20 * health_fragility
            + 0.15 * dollar_pressure
            + 0.15 * vol_stress
            + 0.10 * unwind
            + 0.10 * vix_state
        )

        risk_off_reasons = []
        crash_reasons = []
        if weather_risk >= 0.58:
            risk_off_reasons.append('tactical weather melemah / risk-on support memudar')
        if health_fragility >= 0.65:
            risk_off_reasons.append('market internals rapuh / sempit')
            crash_reasons.append('breadth rapuh bikin cascade lebih mudah')
        if dollar_pressure >= 0.62:
            risk_off_reasons.append('USD pressure mengencang')
            crash_reasons.append('USD squeeze memperbesar stress lintas aset')
        if vol_stress >= 0.62:
            risk_off_reasons.append('vol stress naik')
            crash_reasons.append('vol stress tinggi')
        if unwind >= 0.65:
            risk_off_reasons.append('crowding unwind risk tinggi')
            crash_reasons.append('crowding unwind membuka risiko deleveraging')
        if vix_state >= 0.55:
            risk_off_reasons.append('vol bucket tidak lagi investable')
        if shock_state >= 0.7:
            crash_reasons.append('shock / stress regime aktif')
        if tail_hedge_bid >= 0.65:
            crash_reasons.append('tail-hedge bid naik')
        if tail_state >= 0.7:
            crash_reasons.append('tail state sudah stressed')

        divergence = crash_score - risk_off_score
        if abs(divergence) < 0.08:
            divergence_state = 'aligned'
        elif divergence > 0:
            divergence_state = 'tail_heavier_than_broad_tape'
        else:
            divergence_state = 'broad_defensive_without_full_crash'

        top_reasons = []
        for reason in risk_off_reasons[:3] + crash_reasons[:3]:
            if reason not in top_reasons:
                top_reasons.append(reason)

        return {
            'risk_off_score': risk_off_score,
            'risk_off_state': _state(risk_off_score),
            'crash_score': crash_score,
            'crash_state': _state(crash_score),
            'risk_off_reasons': risk_off_reasons[:5],
            'crash_reasons': crash_reasons[:5],
            'risk_off_vs_crash_divergence': float(divergence),
            'risk_off_vs_crash_divergence_state': divergence_state,
            'top_reasons': top_reasons[:5],
        }
