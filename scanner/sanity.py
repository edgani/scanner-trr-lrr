from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

MARKET_MAX_AGE_DAYS = {
    'us': 10,
    'ihsg': 10,
    'forex': 7,
    'commodities': 7,
    'crypto': 3,
}

MARKET_ABSURD_MOVE = {
    'us': 0.45,
    'ihsg': 0.45,
    'forex': 0.08,
    'commodities': 0.15,
    'crypto': 0.55,
}


@dataclass
class HistorySanity:
    ok: bool
    fresh_ok: bool
    absurd_ok: bool
    as_of: str | None
    age_days: int | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _now_utc() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc)).tz_convert(None)


def evaluate_history_sanity(market: str, df: pd.DataFrame | None) -> HistorySanity:
    if df is None or df.empty:
        return HistorySanity(False, False, False, None, None, 'missing_history')
    if 'Close' not in df.columns:
        return HistorySanity(False, False, False, None, None, 'missing_close')
    last_ts = pd.Timestamp(df.index[-1]).tz_localize(None) if getattr(df.index[-1], 'tzinfo', None) else pd.Timestamp(df.index[-1])
    age_days = int((_now_utc().normalize() - last_ts.normalize()).days)
    fresh_limit = MARKET_MAX_AGE_DAYS.get(market, 7)
    fresh_ok = age_days <= fresh_limit

    close = pd.to_numeric(df['Close'], errors='coerce').dropna()
    if close.empty or close.iloc[-1] <= 0:
        return HistorySanity(False, fresh_ok, False, str(last_ts.date()), age_days, 'bad_last_close')

    absurd_ok = True
    if len(close) >= 3:
        prev = float(close.iloc[-2])
        last = float(close.iloc[-1])
        if prev > 0:
            day_move = abs(last / prev - 1.0)
            absurd_ok = day_move <= MARKET_ABSURD_MOVE.get(market, 0.5)
            if not absurd_ok:
                tail_med = float(close.tail(min(len(close), 20)).median())
                if tail_med > 0:
                    absurd_ok = abs(last / tail_med - 1.0) <= MARKET_ABSURD_MOVE.get(market, 0.5) * 1.75
    if not fresh_ok:
        return HistorySanity(False, False, absurd_ok, str(last_ts.date()), age_days, 'stale_last_bar')
    if not absurd_ok:
        return HistorySanity(False, fresh_ok, False, str(last_ts.date()), age_days, 'absurd_last_move')
    return HistorySanity(True, fresh_ok, absurd_ok, str(last_ts.date()), age_days, '')


def snapshot_market_is_ready(manifest: dict[str, Any]) -> tuple[bool, str]:
    if not manifest:
        return False, 'Manifest belum ada.'
    status = str(manifest.get('snapshot_status') or '').lower()
    if status and status != 'ready':
        return False, str(manifest.get('status_reason') or 'Snapshot belum ready.')
    if int(manifest.get('history_loaded', 0) or 0) <= 0:
        return False, 'History belum kebangun.'
    if int(manifest.get('sanity_rejected_count', 0) or 0) >= int(manifest.get('history_loaded', 0) or 0) and int(manifest.get('history_loaded', 0) or 0) > 0:
        return False, 'Semua history ditolak sanity-check.'
    return True, ''


def stable_close(df: pd.DataFrame | None) -> float | None:
    if df is None or df.empty or 'Close' not in df.columns:
        return None
    close = pd.to_numeric(df['Close'], errors='coerce').dropna()
    if close.empty:
        return None
    v = float(close.iloc[-1])
    return v if np.isfinite(v) and v > 0 else None
