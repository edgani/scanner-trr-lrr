from __future__ import annotations

DISPLAY_OVERRIDES = {
    'EURUSD=X': 'EUR/USD',
    'GBPUSD=X': 'GBP/USD',
    'AUDUSD=X': 'AUD/USD',
    'NZDUSD=X': 'NZD/USD',
    'JPY=X': 'USD/JPY',
    'CHF=X': 'USD/CHF',
    'CAD=X': 'USD/CAD',
    'EURJPY=X': 'EUR/JPY',
    'GBPJPY=X': 'GBP/JPY',
    'AUDJPY=X': 'AUD/JPY',
    'NZDJPY=X': 'NZD/JPY',
    'EURGBP=X': 'EUR/GBP',
    'EURCHF=X': 'EUR/CHF',
    'IDR=X': 'USD/IDR',
    'CNH=X': 'USD/CNH',
    'SGD=X': 'USD/SGD',
    'GC=F': 'XAUUSD',
    'SI=F': 'XAGUSD',
    'CL=F': 'USOIL',
}


def display_symbol(symbol: str) -> str:
    symbol = str(symbol)
    if symbol in DISPLAY_OVERRIDES:
        return DISPLAY_OVERRIDES[symbol]
    if symbol.startswith('CG:'):
        return symbol.split(':', 1)[1].upper()
    if symbol.endswith('-USD'):
        return symbol[:-4].upper()
    return symbol
