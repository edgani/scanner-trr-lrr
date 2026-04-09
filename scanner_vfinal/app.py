from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from config.display_names import display_symbol

ROOT = Path(__file__).resolve().parent
SCAN_DIR = ROOT / "data" / "scans"
MACRO_FILE = ROOT / "data" / "macro" / "latest_macro_snapshot.json"

st.set_page_config(page_title="Scanner Final v33", layout="wide")


def load_macro() -> dict:
    if not MACRO_FILE.exists():
        return {}
    return json.loads(MACRO_FILE.read_text(encoding="utf-8"))


def load_manifest(market: str) -> dict:
    p = SCAN_DIR / f"{market}_scanner_manifest.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _normalize_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    rename_map = {
        "Ticker": "ticker",
        "Bias": "bias",
        "Entry Zone": "entry_zone",
        "Invalidation": "invalidation",
        "Target": "target",
        "Holding Window": "holding_window",
        "Macro Aligned?": "macro_aligned",
        "EV+ / R:R": "ev_rr",
    }
    df = df.rename(columns=rename_map).copy()
    if "display_symbol" not in df.columns:
        base = df.get("ticker", pd.Series(dtype=str)).fillna("")
        df["display_symbol"] = base.map(display_symbol)
    if "ev_rr" not in df.columns and "rr_score" in df.columns and "ev_score" in df.columns:
        df["ev_rr"] = df["ev_score"].round(2).astype(str) + " / " + df["rr_score"].round(2).astype(str)
    if "horizon_bucket" in df.columns:
        horizon_map = {
            "short_term": "Short Term",
            "mid_term": "Mid Term",
            "long_term": "Long Term",
            "next_play": "Next Plays",
            "next_plays": "Next Plays",
            "short": "Short Term",
            "mid": "Mid Term",
            "long": "Long Term",
            "next": "Next Plays",
        }
        df["horizon_label"] = df["horizon_bucket"].astype(str).map(lambda x: horizon_map.get(x, x))
    else:
        df["horizon_label"] = "Unknown"
    if "long_or_short" in df.columns:
        df["side_label"] = df["long_or_short"].astype(str).str.title()
    else:
        df["side_label"] = "Long"
    return df


def load_snapshot(market: str) -> pd.DataFrame:
    p = SCAN_DIR / f"{market}_scanner_snapshot.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    return _normalize_snapshot(df)


def show_table(df: pd.DataFrame, key_prefix: str) -> None:
    if df.empty:
        st.info("Tidak ada kandidat di bucket ini.")
        return
    cols = ["display_symbol", "bias", "entry_zone", "invalidation", "target", "holding_window", "macro_aligned", "ev_rr"]
    view = df[cols].copy().rename(columns={
        "display_symbol": "Ticker",
        "bias": "Bias",
        "entry_zone": "Entry Zone",
        "invalidation": "Invalidation",
        "target": "Target",
        "holding_window": "Holding Window",
        "macro_aligned": "Macro Aligned?",
        "ev_rr": "EV+ / R:R",
    })
    st.dataframe(view, use_container_width=True, hide_index=True)
    options = view["Ticker"].tolist()
    pick = st.selectbox("Detail ticker", options=options, key=f"pick_{key_prefix}")
    row = df.loc[df["display_symbol"] == pick].iloc[0]
    st.markdown(f"**{pick}**")
    st.write(f"Alasan: {row.get('why_now') or row.get('why_not_yet') or '-'}")
    st.write(f"Route: {row.get('route', '-')}")
    st.write(f"Macro explanation: {row.get('macro_explanation', '-')}")
    if row.get("why_not_yet"):
        st.write(f"Why not yet: {row.get('why_not_yet')}")


market = st.sidebar.selectbox("Market", ["us", "ihsg", "forex", "commodities", "crypto"])
macro = load_macro()
man = load_manifest(market)
df = load_snapshot(market)

st.title("Scanner Final v33")

universe = man.get("universe_count", man.get("universe", 0))
history_loaded = man.get("history_loaded")
if history_loaded is None:
    hs = man.get("history_status", {})
    history_loaded = hs.get("present", 0)
eligible = man.get("eligible_count", man.get("eligible", 0))
rows = man.get("rows_count", man.get("rows", len(df)))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Universe", universe)
c2.metric("History loaded", history_loaded)
c3.metric("Eligible", eligible)
c4.metric("Rows", rows)

with st.expander("Macro brain summary", expanded=False):
    st.write({
        "current_quad": macro.get("current_quad") or macro.get("regime") or macro.get("market_bias"),
        "next_quad": macro.get("next_quad") or macro.get("next_route"),
        "execution_mode": macro.get("execution_mode"),
        "safe_harbor": macro.get("safe_harbor") or macro.get("safe_harbor_buckets"),
        "best_beneficiary": macro.get("best_beneficiary"),
    })

if history_loaded == 0:
    st.warning("Starter snapshot untuk market ini belum terisi. Jalankan builder lokal/VPS untuk mengisi market ini.")
elif df.empty:
    st.warning("Snapshot ada, tapi semua kandidat gugur di filter saat ini. Ini bukan karena market hilang.")

if df.empty:
    st.info("Snapshot kosong untuk market ini.")
else:
    tabs = st.tabs(["Short Term", "Mid Term", "Long Term", "Next Plays"])
    for horizon, tab in zip(["Short Term", "Mid Term", "Long Term", "Next Plays"], tabs):
        with tab:
            left, right = st.columns(2)
            with left:
                st.subheader("Long")
                show_table(df[(df["horizon_label"] == horizon) & (df["side_label"] == "Long")], key_prefix=f"{market}_{horizon}_long")
            with right:
                st.subheader("Short")
                show_table(df[(df["horizon_label"] == horizon) & (df["side_label"] == "Short")], key_prefix=f"{market}_{horizon}_short")
