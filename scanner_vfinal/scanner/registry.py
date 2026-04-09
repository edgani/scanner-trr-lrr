from __future__ import annotations

from pathlib import Path
import pandas as pd
from ..config.asset_buckets import bucket_for

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_DIR = ROOT / "data" / "universes"


def load_universe(market: str) -> pd.DataFrame:
    p = UNIVERSE_DIR / f"{market}_universe.csv"
    if not p.exists():
        return pd.DataFrame(columns=["symbol", "name", "market", "bucket"])
    df = pd.read_csv(p)
    if "market" not in df.columns:
        df["market"] = market
    if "name" not in df.columns:
        df["name"] = df["symbol"]
    if "bucket" not in df.columns:
        df["bucket"] = [bucket_for(market, s, n) for s, n in zip(df["symbol"], df["name"])]
    return df
