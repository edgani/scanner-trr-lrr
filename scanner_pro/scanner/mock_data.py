from __future__ import annotations
import hashlib
import numpy as np
import pandas as pd


def _seed_for(symbol: str) -> int:
    digest = hashlib.md5(symbol.encode('utf-8')).hexdigest()[:8]
    return int(digest, 16)


def make_mock_history(symbol: str, bars: int = 420) -> pd.DataFrame:
    rng = np.random.default_rng(_seed_for(symbol))
    drift = rng.normal(0.00035, 0.00025)
    vol = abs(rng.normal(0.02, 0.006))
    shocks = rng.normal(drift, vol, size=bars)
    base = 20 + (rng.random() * 180)
    close = base * np.exp(np.cumsum(shocks))
    high = close * (1 + rng.uniform(0.0005, 0.02, size=bars))
    low = close * (1 - rng.uniform(0.0005, 0.02, size=bars))
    open_ = close * (1 + rng.normal(0, 0.005, size=bars))
    volume = rng.integers(100_000, 8_000_000, size=bars)
    idx = pd.date_range(end=pd.Timestamp.utcnow().normalize(), periods=bars, freq='B')
    df = pd.DataFrame({'Open': open_, 'High': high, 'Low': low, 'Close': close, 'Volume': volume}, index=idx)
    return df.round(4)
