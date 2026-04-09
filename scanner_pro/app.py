from __future__ import annotations

import math
from typing import Any

import pandas as pd
import streamlit as st

from config.settings import APP_SUBTITLE, APP_TITLE, MARKET_LABELS, MARKET_ORDER, SIMPLE_TABLE_COLUMNS
from scanner.snapshot_store import load_snapshot

st.set_page_config(page_title=APP_TITLE, layout="wide")

TOP_TABS = [
    ("short_term", "Short Term"),
    ("mid_term", "Mid Term"),
    ("long_term", "Long Term"),
    ("next_play", "Next Plays"),
]

FOREX_DISPLAY_MAP = {
    "EURUSD=X": "EUR/USD",
    "GBPUSD=X": "GBP/USD",
    "AUDUSD=X": "AUD/USD",
    "NZDUSD=X": "NZD/USD",
    "JPY=X": "USD/JPY",
    "CHF=X": "USD/CHF",
    "CAD=X": "USD/CAD",
    "EURJPY=X": "EUR/JPY",
    "GBPJPY=X": "GBP/JPY",
    "AUDJPY=X": "AUD/JPY",
    "NZDJPY=X": "NZD/JPY",
    "EURGBP=X": "EUR/GBP",
    "EURCHF=X": "EUR/CHF",
    "IDR=X": "USD/IDR",
    "CNH=X": "USD/CNH",
    "SGD=X": "USD/SGD",
}
COMMODITY_DISPLAY_MAP = {
    "GC=F": "XAUUSD",
    "SI=F": "XAGUSD",
    "CL=F": "USOIL",
}


def _human_countdown(value: Any) -> str:
    if value is None:
        return "-"
    text = str(value).strip()
    if not text:
        return "-"
    return text.replace("T-", "").replace("Released", "Sudah rilis")


def _safe_str(value: Any, default: str = "-") -> str:
    if value is None:
        return default
    if isinstance(value, float) and math.isnan(value):
        return default
    text = str(value).strip()
    return text if text else default


def _display_ticker(symbol: Any, market: str) -> str:
    sym = _safe_str(symbol)
    if market == "forex":
        return FOREX_DISPLAY_MAP.get(sym, sym)
    if market == "commodities":
        return COMMODITY_DISPLAY_MAP.get(sym, sym)
    if market == "crypto" and sym.endswith("-USD"):
        return sym.replace("-USD", "/USD")
    return sym


def _prepare_display(df: pd.DataFrame, market: str) -> pd.DataFrame:
    out = df.copy()
    if "Ticker" in out.columns:
        out["Ticker"] = out["Ticker"].map(lambda x: _display_ticker(x, market))
    if "EV+ / R:R" not in out.columns:
        if {"ev_score", "rr_score"}.issubset(out.columns):
            out["EV+ / R:R"] = out.apply(lambda r: f"{float(r['ev_score']):.2f} / {float(r['rr_score']):.2f}", axis=1)
        else:
            out["EV+ / R:R"] = "-"
    return out


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in SIMPLE_TABLE_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    for col in [
        "horizon_bucket", "long_or_short", "detail_kind", "macro_explanation", "route",
        "why_now", "why_not_yet", "ev_score", "rr_score", "raw_states", "current_price",
    ]:
        if col not in out.columns:
            out[col] = ""
    return out


def _show_table(df: pd.DataFrame, key: str, market: str) -> None:
    if df.empty:
        st.info("Belum ada ticker yang lolos filter di bucket ini.")
        return

    view = _prepare_display(_ensure_columns(df), market)
    show = view[SIMPLE_TABLE_COLUMNS].copy()
    st.dataframe(show, use_container_width=True, hide_index=True)

    with st.expander("Detail ticker"):
        picks = view["Ticker"].tolist()
        pick = st.selectbox("Pilih ticker", options=picks, key=f"detail_{key}")
        row = view.loc[view["Ticker"] == pick].iloc[0].to_dict()

        left, right = st.columns(2)
        with left:
            st.markdown(f"**Bias**: {_safe_str(row.get('Bias'))}")
            st.markdown(f"**Entry zone**: {_safe_str(row.get('Entry Zone'))}")
            st.markdown(f"**Invalidation**: {_safe_str(row.get('Invalidation'))}")
            st.markdown(f"**Target**: {_safe_str(row.get('Target'))}")
            st.markdown(f"**Holding window**: {_safe_str(row.get('Holding Window'))}")
            st.markdown(f"**Macro aligned?**: {_safe_str(row.get('Macro Aligned?'))}")
            st.markdown(f"**EV+ / R:R**: {_safe_str(row.get('EV+ / R:R'))}")
        with right:
            st.markdown(f"**Alasan**: {_safe_str(row.get('why_now'))}")
            st.markdown(f"**Route**: {_safe_str(row.get('route'))}")
            st.markdown(f"**Macro explanation**: {_safe_str(row.get('macro_explanation'))}")
            st.markdown(f"**Why not yet**: {_safe_str(row.get('why_not_yet'))}")
            st.markdown(f"**States**: {_safe_str(row.get('raw_states'))}")
            st.markdown(f"**Current price**: {_safe_str(row.get('current_price'))}")


def main() -> None:
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)

    st.sidebar.header("Filter")
    market = st.sidebar.selectbox(
        "Pilih market",
        options=MARKET_ORDER,
        format_func=lambda x: MARKET_LABELS.get(x, x),
        index=0,
    )
    min_ev = st.sidebar.slider("Minimum EV score", min_value=0.0, max_value=10.0, value=0.0, step=0.1)
    show_mixed = st.sidebar.toggle("Tampilkan Macro Mixed", value=True)

    snapshot, manifest = load_snapshot(market)
    if snapshot is None:
        snapshot = pd.DataFrame(columns=SIMPLE_TABLE_COLUMNS)
    snapshot = _ensure_columns(snapshot)

    macro_overlay = manifest.get("macro_overlay", {}) if isinstance(manifest, dict) else {}
    universe = int(manifest.get("universe", 0) or 0)
    eligible = int(manifest.get("eligible", 0) or 0)
    rows = int(manifest.get("rows", len(snapshot)) or len(snapshot))
    coverage = manifest.get("coverage", 0)
    as_of = _safe_str(manifest.get("as_of"))
    hist = manifest.get("history_status", {}) if isinstance(manifest, dict) else {}
    history_present = int(hist.get("present", 0) or 0)
    history_requested = int(hist.get("requested", history_present) or history_present)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Universe", f"{universe:,}")
    m2.metric("History loaded", f"{history_present:,}")
    m3.metric("Eligible", f"{eligible:,}")
    m4.metric("Rows", f"{rows:,}")
    m5.metric("Coverage", f"{coverage}%")
    m6.metric("Snapshot as-of", as_of[:10] if as_of != "-" else "-")

    st.markdown(
        f"**Macro backdrop**: {_safe_str(macro_overlay.get('summary') or macro_overlay.get('market_bias'))}  \
"
        f"**Waktu ke event penting**: {_human_countdown(macro_overlay.get('next_macro_countdown'))}  \
"
        f"**Fokus berikutnya**: {_safe_str(macro_overlay.get('next_macro_focus'))}  \
"
        f"**Mode eksekusi**: {_safe_str(macro_overlay.get('execution_mode'))}"
    )

    if universe > 0:
        st.caption(
            f"Universe terdaftar: {universe:,}. History yang sudah kebangun: {history_present:,}. "
            f"Kalau angka history jauh lebih kecil dari universe, berarti ini belum full-universe build; hasil scanner masih parsial."
        )

    if snapshot.empty:
        if universe > 0:
            if history_present == 0:
                st.warning("Universe sudah ada, tapi history belum kebangun. Jalankan build full supaya universe ini benar-benar terisi.")
            else:
                st.info("Snapshot ada tapi belum ada ticker yang lolos filter saat ini. Ini bukan berarti universe kosong; hanya belum ada setup yang lolos di starter/build terakhir.")
            st.caption(f"Status build sekarang: history loaded {history_present:,} dari universe {universe:,}. Requested terakhir: {history_requested:,}.")
        else:
            st.warning("Snapshot belum ada atau kosong. Jalankan scripts/update_full_history.py lalu scripts/build_all_snapshots.py.")
        return

    filtered = snapshot.copy()
    filtered["ev_score"] = pd.to_numeric(filtered["ev_score"], errors="coerce").fillna(0.0)
    filtered["rr_score"] = pd.to_numeric(filtered["rr_score"], errors="coerce").fillna(0.0)
    filtered = filtered[filtered["ev_score"] >= min_ev]
    if not show_mixed:
        filtered = filtered[filtered["Macro Aligned?"] != "Mixed"]

    top_tabs = st.tabs([label for _, label in TOP_TABS])
    for tab, (bucket, _label) in zip(top_tabs, TOP_TABS):
        with tab:
            long_df = filtered[(filtered["horizon_bucket"] == bucket) & (filtered["long_or_short"] == "Long")].sort_values(["ev_score", "rr_score"], ascending=False)
            short_df = filtered[(filtered["horizon_bucket"] == bucket) & (filtered["long_or_short"] == "Short")].sort_values(["ev_score", "rr_score"], ascending=False)
            sub1, sub2 = st.tabs(["Long", "Short"])
            with sub1:
                _show_table(long_df, f"{bucket}_long", market)
            with sub2:
                _show_table(short_df, f"{bucket}_short", market)


if __name__ == "__main__":
    main()
