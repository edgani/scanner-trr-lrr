from __future__ import annotations

DISPLAY_OVERRIDES = {
    "EURUSD=X": "EUR/USD",
    "GBPUSD=X": "GBP/USD",
    "JPY=X": "USD/JPY",
    "AUDUSD=X": "AUD/USD",
    "NZDUSD=X": "NZD/USD",
    "CAD=X": "USD/CAD",
    "CHF=X": "USD/CHF",
    "EURJPY=X": "EUR/JPY",
    "GBPJPY=X": "GBP/JPY",
    "IDR=X": "USD/IDR",
    "GC=F": "XAUUSD",
    "SI=F": "XAGUSD",
    "CL=F": "USOIL",
}

def display_symbol(symbol: str) -> str:
    return DISPLAY_OVERRIDES.get(symbol, symbol.replace("-USD", "/USD"))
