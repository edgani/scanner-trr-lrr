from __future__ import annotations

import pandas as pd


def rank(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    score = df["ev_score"].fillna(0) * df["macro_score"].fillna(0) * df["readiness_score"].fillna(0)
    score = score * df["conviction_score"].fillna(0) - df["penalty_score"].fillna(0)
    out = df.copy()
    out["final_rank_score"] = score
    return out.sort_values(["final_rank_score", "rr_score"], ascending=[False, False])
