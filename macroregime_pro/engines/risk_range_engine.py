from __future__ import annotations
from typing import Dict
import numpy as np
import pandas as pd

from config.weights import RISK_RANGE_WEIGHTS
from utils.math_utils import clamp01


def _safe_series(s) -> pd.Series:
    if isinstance(s, pd.Series):
        return pd.to_numeric(s, errors="coerce").dropna()
    return pd.Series(dtype=float)


def _range_state(width_pct: float) -> str:
    if width_pct >= 0.12:
        return 'wide'
    if width_pct <= 0.05:
        return 'narrow'
    return 'normal'


def _stretch_state(px: float, low: float, mid: float, high: float) -> str:
    if not np.isfinite(px) or not np.isfinite(low) or not np.isfinite(high) or not np.isfinite(mid):
        return 'neutral'
    band = max(high - low, 1e-9)
    if px <= low + 0.12 * band:
        return 'oversold'
    if px >= high - 0.12 * band:
        return 'overbought'
    return 'neutral'


class RiskRangeEngine:
    def run(
        self,
        prices: Dict[str, pd.Series],
        market: Dict[str, float],
        vol_credit: Dict[str, float],
        positioning: Dict[str, float],
        derivatives: Dict[str, float],
        shock: Dict[str, object],
    ) -> Dict[str, object]:
        spy = _safe_series(prices.get('SPY'))
        if len(spy) < 40:
            return {
                'anchor_symbol': 'SPY',
                'trade_mid': None,
                'trade_low': None,
                'trade_high': None,
                'range_width_pct': None,
                'range_state': 'unknown',
                'stretch_state': 'neutral',
                'downside_buffer': None,
                'upside_buffer': None,
                'notes': ['Risk range belum bisa dihitung karena data SPY tidak cukup.'],
            }

        px = float(spy.iloc[-1])
        ema5 = float(spy.ewm(span=5, adjust=False).mean().iloc[-1])
        rets = spy.pct_change().dropna()
        rv21 = float(rets.tail(21).std()) if len(rets) >= 21 else float(rets.std())
        realized_vol = clamp01(rv21 / 0.03)
        dollar_pressure = clamp01(0.5 + float(market.get('dxy_1m', 0.0)) / 0.04)
        vol_stress = clamp01(float(vol_credit.get('vol_stress', 0.5)))
        crowding = clamp01(float(positioning.get('crowding_proxy', positioning.get('crowding', 0.5))))
        shock_penalty = 1.0 if str(shock.get('state', 'normal')) == 'shock' else 0.6 if str(shock.get('state', 'normal')) == 'stress' else 0.25 if str(shock.get('state', 'normal')) == 'watch' else 0.0
        tail_hedge_bid = clamp01(float(derivatives.get('tail_hedge_bid', 0.5)))

        width_driver = (
            RISK_RANGE_WEIGHTS['realized_vol'] * realized_vol
            + RISK_RANGE_WEIGHTS['dollar_pressure'] * dollar_pressure
            + RISK_RANGE_WEIGHTS['vol_stress'] * vol_stress
            + RISK_RANGE_WEIGHTS['crowding'] * crowding
            + RISK_RANGE_WEIGHTS['shock'] * shock_penalty
            + RISK_RANGE_WEIGHTS['tail_hedge_bid'] * tail_hedge_bid
        )
        width_driver = clamp01(width_driver)
        width_pct = 0.025 + 0.12 * width_driver
        width = ema5 * width_pct

        low = float(ema5 - width)
        high = float(ema5 + width)
        stretch = _stretch_state(px, low, ema5, high)
        notes = [
            f"Range anchor pakai SPY dengan width driver {width_driver:.2f}.",
            f"Dollar pressure {dollar_pressure:.2f}, vol stress {vol_stress:.2f}, crowding {crowding:.2f}.",
        ]
        if shock_penalty >= 0.6:
            notes.append('Shock regime aktif; range diperlebar untuk jaga false comfort.')
        if tail_hedge_bid >= 0.65:
            notes.append('Tail-hedge bid tinggi; downside range dianggap lebih relevan dari upside chase.')

        return {
            'anchor_symbol': 'SPY',
            'trade_mid': float(ema5),
            'trade_low': low,
            'trade_high': high,
            'range_width_pct': float(width_pct),
            'range_state': _range_state(width_pct),
            'stretch_state': stretch,
            'downside_buffer': float((px - low) / max(px, 1e-9)),
            'upside_buffer': float((high - px) / max(px, 1e-9)),
            'notes': notes,
        }
