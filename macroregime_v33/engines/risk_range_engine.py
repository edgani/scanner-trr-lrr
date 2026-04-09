from __future__ import annotations
from typing import Dict
import math
import numpy as np
import pandas as pd

from utils.math_utils import clamp01


PRICE_COLS = ["Open", "High", "Low", "Close", "Volume"]


def _safe_series(s) -> pd.Series:
    if isinstance(s, pd.Series):
        ser = pd.to_numeric(s, errors="coerce").dropna()
    elif isinstance(s, pd.DataFrame) and "Close" in s.columns:
        ser = pd.to_numeric(s["Close"], errors="coerce").dropna()
    else:
        ser = pd.Series(dtype=float)
    if not ser.empty:
        idx = pd.to_datetime(ser.index, errors="coerce")
        if getattr(idx, 'tz', None) is not None:
            idx = idx.tz_convert('UTC').tz_localize(None)
        ser.index = idx
        ser = ser[~ser.index.isna()].sort_index()
        ser = ser[~ser.index.duplicated(keep='last')]
    return ser


def _frame_from_any(obj, fallback_series: pd.Series | None = None) -> pd.DataFrame:
    if isinstance(obj, pd.DataFrame) and not obj.empty:
        frame = obj.copy()
        frame.columns = [str(c[-1] if isinstance(c, tuple) else c) for c in frame.columns]
        out = pd.DataFrame(index=pd.to_datetime(frame.index, errors='coerce'))
        if getattr(out.index, 'tz', None) is not None:
            out.index = out.index.tz_convert('UTC').tz_localize(None)
        if 'Close' in frame.columns:
            out['Close'] = pd.to_numeric(frame['Close'], errors='coerce')
        else:
            nums = frame.select_dtypes(include=[np.number])
            if nums.empty:
                out['Close'] = np.nan
            else:
                out['Close'] = pd.to_numeric(nums.iloc[:, 0], errors='coerce')
        out['Open'] = pd.to_numeric(frame.get('Open', out['Close']), errors='coerce')
        out['High'] = pd.to_numeric(frame.get('High', pd.concat([out['Open'], out['Close']], axis=1).max(axis=1)), errors='coerce')
        out['Low'] = pd.to_numeric(frame.get('Low', pd.concat([out['Open'], out['Close']], axis=1).min(axis=1)), errors='coerce')
        out['Volume'] = pd.to_numeric(frame.get('Volume', np.nan), errors='coerce')
        out = out[~out.index.isna()].sort_index()
        out = out[~out.index.duplicated(keep='last')]
        out = out.dropna(subset=['Close'])
        return out[PRICE_COLS] if not out.empty else pd.DataFrame(columns=PRICE_COLS)
    close = _safe_series(fallback_series)
    if close.empty:
        return pd.DataFrame(columns=PRICE_COLS)
    out = pd.DataFrame(index=close.index)
    out['Close'] = close.astype(float)
    out['Open'] = out['Close']
    out['High'] = out['Close']
    out['Low'] = out['Close']
    out['Volume'] = np.nan
    return out[PRICE_COLS]


def _range_state(width_pct: float) -> str:
    if not math.isfinite(width_pct):
        return 'unknown'
    if width_pct >= 0.12:
        return 'wide'
    if width_pct <= 0.05:
        return 'narrow'
    return 'normal'


def _stretch_state(px: float, low: float, mid: float, high: float) -> str:
    if not all(math.isfinite(x) for x in [px, low, mid, high]):
        return 'neutral'
    band = max(high - low, 1e-9)
    pos = (px - low) / band
    if pos <= 0.12:
        return 'oversold'
    if pos >= 0.88:
        return 'overbought'
    if pos <= 0.25:
        return 'reset_zone'
    if pos >= 0.75:
        return 'extended'
    return 'neutral'


def _atr_pct(frame: pd.DataFrame, n: int = 14) -> float:
    if frame.empty or len(frame) < n + 1:
        return 0.0
    high = pd.to_numeric(frame['High'], errors='coerce')
    low = pd.to_numeric(frame['Low'], errors='coerce')
    close = pd.to_numeric(frame['Close'], errors='coerce')
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = float(tr.tail(n).mean()) if not tr.dropna().empty else 0.0
    last_close = float(close.iloc[-1]) if len(close) else 0.0
    if not math.isfinite(last_close) or last_close <= 0:
        return 0.0
    return max(0.0, atr / last_close)


def _realized_vol(close: pd.Series, n: int = 21) -> float:
    close = _safe_series(close)
    if len(close) < n + 1:
        return 0.0
    ret = close.pct_change().dropna().tail(n)
    return float(ret.std()) if not ret.empty else 0.0


def _fair_value_fast(close: pd.Series) -> float:
    close = _safe_series(close)
    if close.empty:
        return float('nan')
    ema10 = float(close.ewm(span=10, adjust=False).mean().iloc[-1])
    ema21 = float(close.ewm(span=21, adjust=False).mean().iloc[-1])
    return 0.65 * ema10 + 0.35 * ema21


def _fair_value_slow(close: pd.Series) -> float:
    close = _safe_series(close)
    if close.empty:
        return float('nan')
    return float(close.ewm(span=34, adjust=False).mean().iloc[-1])


def _trend_state(close: pd.Series) -> str:
    close = _safe_series(close)
    if len(close) < 35:
        return 'unknown'
    px = float(close.iloc[-1])
    ema21 = float(close.ewm(span=21, adjust=False).mean().iloc[-1])
    ema34 = float(close.ewm(span=34, adjust=False).mean().iloc[-1])
    slope21 = float(close.ewm(span=21, adjust=False).mean().diff().tail(5).mean())
    if px > ema21 > ema34 and slope21 > 0:
        return 'bullish'
    if px < ema21 < ema34 and slope21 < 0:
        return 'bearish'
    return 'transitional'


def _break_state(px: float, trade_low: float, trade_high: float, trend_low: float, trend_high: float) -> str:
    if not all(math.isfinite(x) for x in [px, trade_low, trade_high, trend_low, trend_high]):
        return 'unknown'
    if px > trade_high and px > trend_high:
        return 'upside_escape'
    if px < trade_low and px < trend_low:
        return 'downside_break'
    if px > trade_high:
        return 'trade_breakout'
    if px < trade_low:
        return 'trade_breakdown'
    if trend_low <= px <= trend_high:
        return 'inside_trend_range'
    return 'inside_trade_range'


def _volume_confirm(frame: pd.DataFrame) -> float:
    if frame.empty or 'Volume' not in frame.columns:
        return 0.5
    vol = pd.to_numeric(frame['Volume'], errors='coerce').dropna()
    if len(vol) < 20:
        return 0.5
    avg20 = float(vol.tail(20).mean())
    last = float(vol.iloc[-1])
    if not math.isfinite(avg20) or avg20 <= 0:
        return 0.5
    ratio = last / avg20
    return clamp01(0.25 + 0.50 * min(max(ratio, 0.0), 2.0) / 2.0)


class RiskRangeEngine:
    def run(
        self,
        prices: Dict[str, pd.Series],
        price_frames: Dict[str, pd.DataFrame] | None,
        market: Dict[str, float],
        vol_credit: Dict[str, float],
        positioning: Dict[str, float],
        derivatives: Dict[str, float],
        shock: Dict[str, object],
        symbols: list[str] | None = None,
    ) -> Dict[str, object]:
        keys = symbols or sorted({*(prices or {}).keys(), *((price_frames or {}).keys())})
        if not keys:
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
                'asset_ranges': {},
                'notes': ['Risk range belum bisa dihitung karena belum ada price data.'],
                'model': 'asset_native_v1',
                'asset_range_coverage': 0,
            }

        dollar_pressure = clamp01(0.5 + float(market.get('dxy_1m', 0.0)) / 0.04)
        vol_stress = clamp01(float(vol_credit.get('vol_stress', derivatives.get('vol_stress', 0.5))))
        crowding = clamp01(float(positioning.get('crowding_proxy', positioning.get('crowding', 0.5))))
        shock_penalty = 1.0 if str(shock.get('state', 'normal')) == 'shock' else 0.65 if str(shock.get('state', 'normal')) == 'stress' else 0.30 if str(shock.get('state', 'normal')) == 'watch' else 0.0
        tail_hedge_bid = clamp01(float(derivatives.get('tail_hedge_bid', 0.5)))
        stress_scalar = 1.0 + 0.35 * shock_penalty + 0.20 * vol_stress + 0.10 * crowding
        down_asym = 1.0 + 0.20 * dollar_pressure + 0.20 * tail_hedge_bid
        up_asym = max(0.80, 1.0 - 0.08 * min(dollar_pressure, 0.8))

        asset_ranges: Dict[str, dict] = {}
        for sym in keys:
            close = _safe_series((prices or {}).get(sym))
            frame = _frame_from_any((price_frames or {}).get(sym), close)
            close = _safe_series(frame['Close'] if not frame.empty and 'Close' in frame.columns else close)
            if len(close) < 35:
                continue
            px = float(close.iloc[-1])
            fast = _fair_value_fast(close)
            slow = _fair_value_slow(close)
            atr_pct = _atr_pct(frame, 14)
            rv21 = _realized_vol(close, 21)
            base_vol = max(0.004, 0.55 * atr_pct + 0.45 * rv21)
            trade_width_pct = base_vol * 1.20 * stress_scalar
            trend_width_pct = base_vol * 2.10 * stress_scalar
            trade_low = float(fast * (1.0 - trade_width_pct * down_asym))
            trade_high = float(fast * (1.0 + trade_width_pct * up_asym))
            trend_low = float(slow * (1.0 - trend_width_pct * down_asym))
            trend_high = float(slow * (1.0 + trend_width_pct * up_asym))
            stretch = _stretch_state(px, trade_low, fast, trade_high)
            break_state = _break_state(px, trade_low, trade_high, trend_low, trend_high)
            volume_confirm = _volume_confirm(frame)
            trend_state = _trend_state(close)
            range_quality = clamp01(0.45 * (1.0 - min(trade_width_pct, 0.30) / 0.30) + 0.35 * volume_confirm + 0.20 * (0.5 if trend_state == 'transitional' else 0.85))
            confidence = clamp01(0.35 * volume_confirm + 0.30 * (0.85 if trend_state != 'transitional' else 0.45) + 0.20 * (1.0 - min(shock_penalty, 1.0)) + 0.15 * (1.0 - min(crowding, 1.0)))
            asset_ranges[sym] = {
                'trade_mid': float(fast),
                'trade_low': trade_low,
                'trade_high': trade_high,
                'trend_mid': float(slow),
                'trend_low': trend_low,
                'trend_high': trend_high,
                'tail_floor': float(trend_low * (1.0 - 0.60 * base_vol * down_asym)),
                'tail_ceiling': float(trend_high * (1.0 + 0.40 * base_vol * up_asym)),
                'range_width_pct': float(trade_width_pct),
                'range_state': _range_state(trade_width_pct),
                'stretch_state': stretch,
                'trend_state': trend_state,
                'break_state': break_state,
                'volume_confirm': float(volume_confirm),
                'range_quality': float(range_quality),
                'signal_confidence': float(confidence),
                'has_ohlcv': bool(not frame.empty),
                'bar_count': int(len(close)),
            }

        anchor_symbol = 'SPY' if 'SPY' in asset_ranges else (next(iter(asset_ranges.keys())) if asset_ranges else 'SPY')
        anchor = asset_ranges.get(anchor_symbol, {})
        px = float(_safe_series((prices or {}).get(anchor_symbol)).iloc[-1]) if anchor_symbol in (prices or {}) and not _safe_series((prices or {}).get(anchor_symbol)).empty else float('nan')
        trade_low = anchor.get('trade_low')
        trade_high = anchor.get('trade_high')
        downside_buffer = float((px - trade_low) / max(px, 1e-9)) if math.isfinite(px) and isinstance(trade_low, (int, float)) else None
        upside_buffer = float((trade_high - px) / max(px, 1e-9)) if math.isfinite(px) and isinstance(trade_high, (int, float)) else None
        notes = [
            f'Risk range model asset-native v1 aktif untuk {len(asset_ranges)} aset.',
            f'Driver stress: dollar {dollar_pressure:.2f}, vol {vol_stress:.2f}, crowding {crowding:.2f}, shock {shock_penalty:.2f}.',
        ]
        if shock_penalty >= 0.65:
            notes.append('Shock regime aktif; trade dan trend range diperlebar lintas aset.')
        if tail_hedge_bid >= 0.65:
            notes.append('Tail-hedge bid tinggi; downside asymmetry dibesarkan.')

        summary = {
            'wide_count': sum(1 for v in asset_ranges.values() if v.get('range_state') == 'wide'),
            'narrow_count': sum(1 for v in asset_ranges.values() if v.get('range_state') == 'narrow'),
            'bullish_count': sum(1 for v in asset_ranges.values() if v.get('trend_state') == 'bullish'),
            'bearish_count': sum(1 for v in asset_ranges.values() if v.get('trend_state') == 'bearish'),
        }
        return {
            'anchor_symbol': anchor_symbol,
            'trade_mid': anchor.get('trade_mid'),
            'trade_low': trade_low,
            'trade_high': trade_high,
            'range_width_pct': anchor.get('range_width_pct'),
            'range_state': anchor.get('range_state', 'unknown'),
            'stretch_state': anchor.get('stretch_state', 'neutral'),
            'downside_buffer': downside_buffer,
            'upside_buffer': upside_buffer,
            'asset_ranges': asset_ranges,
            'summary': summary,
            'notes': notes,
            'model': 'asset_native_v1',
            'asset_range_coverage': int(len(asset_ranges)),
        }
