from __future__ import annotations
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / 'data'
SCANS_DIR = DATA_DIR / 'scans'
UNIVERSES_DIR = DATA_DIR / 'universes'
MACRO_DIR = DATA_DIR / 'macro'
HISTORY_DIR = DATA_DIR / 'history'
LOGS_DIR = DATA_DIR / 'logs'

DEFAULT_HISTORY_PERIOD = 'max'
DEFAULT_INTERVAL = '1d'
MIN_HISTORY_BARS = 180
PRICE_CHUNK_SIZE = {
    'us': 50,
    'ihsg': 40,
    'crypto': 30,
    'forex': 20,
    'commodities': 10,
}
MARKET_LABELS = {
    'us': 'US Stocks',
    'ihsg': 'IHSG',
    'forex': 'Forex',
    'commodities': 'Commodities',
    'crypto': 'Crypto',
}
MARKET_ORDER = ['us', 'ihsg', 'forex', 'commodities', 'crypto']
APP_TITLE = 'Scanner Pro Final'
APP_SUBTITLE = 'Short / Mid / Long execute-now board with Next Plays watchlist'
RISK_REWARD_MIN = {
    'short_term': 1.6,
    'mid_term': 2.0,
    'long_term': 2.5,
    'next_play': 1.2,
}
HOLDING_WINDOWS = {
    'short_term': '2-10 hari',
    'mid_term': '1-4 minggu',
    'long_term': '1-6 bulan',
    'next_play': 'belum siap sekarang',
}
FOREX_MAJOR_PAIRS = [
    'EURUSD=X','GBPUSD=X','AUDUSD=X','NZDUSD=X','JPY=X','CHF=X','CAD=X',
    'EURJPY=X','GBPJPY=X','AUDJPY=X','NZDJPY=X','EURGBP=X','EURCHF=X','IDR=X','CNH=X','SGD=X'
]
COMMODITY_SYMBOLS = ['GC=F','SI=F','CL=F']
SIMPLE_TABLE_COLUMNS = ['Ticker','Bias','Entry Zone','Invalidation','Target','Holding Window','Macro Aligned?','EV+ / R:R']
