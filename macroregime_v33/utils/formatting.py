from __future__ import annotations

from typing import Iterable

FRIENDLY_LABELS = {
    "GC=F": "XAUUSD",
    "SI=F": "XAGUSD",
    "CL=F": "WTI",
    "BZ=F": "BRENT",
    "HG=F": "COPPER",
    "NG=F": "NATGAS",
    "BTC-USD": "BTCUSD",
    "ETH-USD": "ETHUSD",
    "SOL-USD": "SOLUSD",
    "LINK-USD": "LINKUSD",
    "MKR-USD": "MKRUSD",
    "AVAX-USD": "AVAXUSD",
    "XRP-USD": "XRPUSD",
    "ADA-USD": "ADAUSD",
    "TAO22974-USD": "TAOUSD",
    "RENDER-USD": "RENDERUSD",
    "FET-USD": "FETUSD",
    "ONDO-USD": "ONDOUSD",
    "WIF-USD": "WIFUSD",
    "IDR=X": "USD/IDR",
    "JPY=X": "USD/JPY",
    "CAD=X": "USD/CAD",
    "CHF=X": "USD/CHF",
    "EURUSD=X": "EUR/USD",
    "AUDUSD=X": "AUD/USD",
    "NZDUSD=X": "NZD/USD",
    "GBPUSD=X": "GBP/USD",
    "EURJPY=X": "EUR/JPY",
    "BBCA.JK": "BBCA",
    "BBRI.JK": "BBRI",
    "BMRI.JK": "BMRI",
    "BBNI.JK": "BBNI",
    "ADRO.JK": "ADRO",
    "PTBA.JK": "PTBA",
    "ITMG.JK": "ITMG",
    "BUMI.JK": "BUMI",
    "ANTM.JK": "ANTM",
    "INCO.JK": "INCO",
    "MDKA.JK": "MDKA",
    "TINS.JK": "TINS",
    "MEDC.JK": "MEDC",
    "PGEO.JK": "PGEO",
    "UNVR.JK": "UNVR",
    "ASII.JK": "ASII",
    "^JKSE": "IHSG",
    "^VIX": "VIX",
    "EEM": "EEM",
}


def pct(x: float, nd: int = 1) -> str:
    try:
        return f"{100 * float(x):.{nd}f}%"
    except Exception:
        return "—"


def num(x: float, nd: int = 2) -> str:
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return "—"


def label_value(symbol: str) -> str:
    text = str(symbol)
    return FRIENDLY_LABELS.get(text, text)


def label_join(symbols: Iterable[str]) -> str:
    items = [label_value(x) for x in symbols if str(x).strip()]
    return ", ".join(items) if items else "—"


def fmt_price(symbol: str, value: float | None) -> str:
    try:
        v = float(value)
    except Exception:
        return "—"
    s = str(symbol)
    if s.endswith("=X"):
        if s == "IDR=X":
            return f"{v:,.0f}"
        return f"{v:,.4f}"
    if s.endswith("-USD"):
        if v >= 1000:
            return f"{v:,.0f}"
        if v >= 100:
            return f"{v:,.2f}"
        return f"{v:,.3f}"
    if s.endswith(".JK"):
        return f"{v:,.0f}"
    if s in {"GC=F", "SI=F", "CL=F", "BZ=F", "HG=F", "NG=F"}:
        return f"{v:,.2f}"
    if v >= 1000:
        return f"{v:,.0f}"
    return f"{v:,.2f}"
