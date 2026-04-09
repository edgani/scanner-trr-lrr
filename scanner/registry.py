from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_DIR = ROOT / 'data' / 'universes'

BUNDLE_FILES = {
    'us': 'us_full_universe.json',
    'ihsg': 'ihsg_full_universe.json',
    'crypto': 'crypto_full_universe.json',
    'forex': 'fx_full_universe.json',
    'commodities': 'commodities_full_universe.json',
}

FX_DISPLAY = {
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
}

COMMODITY_DISPLAY = {
    'GC=F': 'XAUUSD',
    'SI=F': 'XAGUSD',
    'CL=F': 'USOIL',
}

US_BUCKETS = {
    'AAPL': 'quality_growth',
    'MSFT': 'quality_growth',
    'NVDA': 'semis_beta',
    'AMZN': 'consumer_cyc',
    'GOOG': 'quality_growth',
    'GOOGL': 'quality_growth',
    'META': 'quality_growth',
    'TSLA': 'high_beta',
    'XOM': 'energy',
    'CVX': 'energy',
    'JPM': 'financials',
}
IHSG_BUCKETS = {
    'BBCA.JK': 'banks',
    'BBRI.JK': 'banks',
    'BMRI.JK': 'banks',
    'BBNI.JK': 'banks',
    'TLKM.JK': 'telco_defensive',
    'ASII.JK': 'cyclical',
    'ICBP.JK': 'telco_defensive',
    'ADRO.JK': 'energy_exporter',
    'ANTM.JK': 'metals_energy',
    'MDKA.JK': 'metals_energy',
}
FOREX_BUCKETS = {
    'EURUSD=X': 'usd_major',
    'GBPUSD=X': 'usd_major',
    'AUDUSD=X': 'commodity_fx',
    'NZDUSD=X': 'commodity_fx',
    'JPY=X': 'jpy_safe_haven',
    'CHF=X': 'safe_haven_fx',
    'CAD=X': 'commodity_fx',
    'EURJPY=X': 'carry_beta',
    'GBPJPY=X': 'carry_beta',
    'AUDJPY=X': 'carry_beta',
    'NZDJPY=X': 'carry_beta',
    'EURGBP=X': 'usd_major',
    'EURCHF=X': 'safe_haven_fx',
    'IDR=X': 'em_fx',
    'CNH=X': 'em_fx',
    'SGD=X': 'em_fx',
}
COMMODITY_BUCKETS = {
    'GC=F': 'precious',
    'SI=F': 'precious',
    'CL=F': 'energy',
}


def _candidate_macro_roots() -> list[Path]:
    env_root = os.getenv('SCANNER_MACRO_ROOT')
    out: list[Path] = []
    if env_root:
        out.append(Path(env_root))
    parent = ROOT.parent
    out.extend([
        parent / 'v33_final',
        parent / 'macroregime_v33',
        parent / 'MacroRegime_Pro_v33_final_mentok',
    ])
    for p in parent.iterdir():
        if p.is_dir() and (p / '.cache' / 'latest_snapshot.json').exists():
            out.append(p)
    dedup: list[Path] = []
    seen: set[str] = set()
    for p in out:
        rp = str(p.resolve()) if p.exists() else str(p)
        if rp not in seen:
            dedup.append(p)
            seen.add(rp)
    return dedup


def _macro_root() -> Path:
    for p in _candidate_macro_roots():
        if (p / '.cache' / 'universe').exists():
            return p
    return ROOT.parent / 'v33_final'


def _macro_universe_dir() -> Path:
    return _macro_root() / '.cache' / 'universe'


def _load_bundle(market: str) -> dict[str, Any]:
    path = _macro_universe_dir() / BUNDLE_FILES[market]
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def _clean_name(name: str, symbol: str) -> str:
    txt = str(name or symbol).strip()
    return txt if txt else symbol


def bucket_for(market: str, symbol: str, name: str = '', extra: dict[str, Any] | None = None) -> str:
    market = market.lower()
    name_l = str(name or '').lower()
    extra = extra or {}
    if market == 'us':
        if symbol in US_BUCKETS:
            return US_BUCKETS[symbol]
        if any(k in name_l for k in ['warrant', 'rights', 'unit', 'acquisition', 'blank check', 'spac']):
            return 'junk_structure'
        if any(k in name_l for k in ['energy', 'oil', 'gas', 'petroleum', 'uranium']):
            return 'energy'
        if any(k in name_l for k in ['bank', 'capital', 'financial', 'insurance', 'payments']):
            return 'financials'
        if any(k in name_l for k in ['semiconductor', 'chip']):
            return 'semis_beta'
        if any(k in name_l for k in ['software', 'cloud', 'cyber', 'data', 'ai', 'technology']):
            return 'quality_growth'
        if any(k in name_l for k in ['pharma', 'health', 'utility', 'telecom', 'staples']):
            return 'defensives'
        if any(k in name_l for k in ['consumer', 'retail', 'travel', 'restaurant', 'hotel', 'leisure', 'automotive']):
            return 'consumer_cyc'
        return 'small_beta'
    if market == 'ihsg':
        if symbol in IHSG_BUCKETS:
            return IHSG_BUCKETS[symbol]
        if any(k in name_l for k in ['bank', 'bca', 'bri', 'mandiri', 'bni']):
            return 'banks'
        if any(k in name_l for k in ['coal', 'energy', 'mining', 'oil', 'gas']):
            return 'energy_exporter'
        if any(k in name_l for k in ['nickel', 'metal', 'emas', 'gold', 'copper', 'timah']):
            return 'metals_energy'
        if any(k in name_l for k in ['telekom', 'tower', 'infra', 'pelabuhan']):
            return 'telco_defensive'
        return 'cyclical'
    if market == 'forex':
        return FOREX_BUCKETS.get(symbol, 'usd_major')
    if market == 'commodities':
        return COMMODITY_BUCKETS.get(symbol, 'other_commodity')

    coin_id = str(extra.get('coin_id') or '').lower()
    raw_symbol = str(extra.get('raw_symbol') or '').upper()
    text = f'{symbol} {name_l} {coin_id} {raw_symbol}'.lower()
    if any(k in text for k in ['2x', '3x', '5x', '10x', ' leveraged', 'inverse', 'short ', ' long ']):
        return 'micro_alt'
    if any(k in text for k in ['bitcoin', ' btc ']) or raw_symbol == 'BTC':
        return 'btc_quality'
    if raw_symbol in {'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX'} or any(k in text for k in ['ethereum', 'solana', 'binance', 'ripple', 'cardano', 'avalanche']):
        return 'majors'
    if raw_symbol in {'ARB', 'OP', 'MATIC', 'APT', 'SUI', 'NEAR', 'TON', 'TIA', 'SEI'} or any(k in text for k in ['arbitrum', 'optimism', 'matic', 'polygon', 'aptos', 'sui', 'near', 'ton', 'celestia']):
        return 'l1l2'
    if raw_symbol in {'AAVE', 'MKR', 'CRV', 'COMP', 'LDO', 'UNI'} or any(k in text for k in ['aave', 'maker', 'curve', 'compound', 'lido', 'uniswap']):
        return 'defi'
    if raw_symbol in {'RENDER', 'RNDR', 'FET', 'TAO', 'GRT'} or any(k in text for k in ['render', 'fetch', 'bittensor', 'graph']):
        return 'ai_data'
    if raw_symbol in {'ONDO', 'LINK', 'PYTH', 'INJ'} or any(k in text for k in ['ondo', 'chainlink', 'pyth', 'injective']):
        return 'infra'
    if raw_symbol in {'DOGE', 'PEPE', 'BONK', 'WIF', 'FLOKI'} or any(k in text for k in ['doge', 'pepe', 'bonk', 'wif', 'floki']):
        return 'meme_beta'
    if raw_symbol in {'WLD', 'JUP', 'ENA', 'TIA'}:
        return 'high_beta'
    return 'micro_alt'


def _bundle_to_frame(market: str) -> pd.DataFrame:
    payload = _load_bundle(market)
    records = payload.get('records', []) if isinstance(payload, dict) else []
    rows: list[dict[str, Any]] = []
    for rec in records:
        symbol = str(rec.get('symbol', '')).strip()
        if not symbol:
            continue
        if market == 'commodities' and symbol not in COMMODITY_BUCKETS:
            continue
        name = _clean_name(rec.get('name') or rec.get('code') or FX_DISPLAY.get(symbol) or COMMODITY_DISPLAY.get(symbol), symbol)
        row = {
            'symbol': symbol,
            'name': name,
            'market': market,
            'display_symbol': FX_DISPLAY.get(symbol) or COMMODITY_DISPLAY.get(symbol) or symbol,
        }
        if market == 'crypto':
            row['coingecko_id'] = rec.get('coin_id')
            row['raw_symbol'] = rec.get('raw_symbol')
        row['bucket'] = bucket_for(market, symbol, name, rec)
        rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=['symbol', 'name', 'market', 'bucket', 'display_symbol'])
    return df.drop_duplicates(subset=['symbol']).sort_values('symbol').reset_index(drop=True)


@lru_cache(maxsize=16)
def load_universe(market: str, force_bundle: bool = False) -> pd.DataFrame:
    market = market.lower()
    csv_path = UNIVERSE_DIR / f'{market}_universe.csv'
    if csv_path.exists() and not force_bundle:
        df = pd.read_csv(csv_path)
        if 'bucket' not in df.columns:
            df['bucket'] = [bucket_for(market, str(s), str(n)) for s, n in zip(df['symbol'], df.get('name', df['symbol']))]
        if 'display_symbol' not in df.columns:
            df['display_symbol'] = df['symbol'].map(lambda s: FX_DISPLAY.get(str(s)) or COMMODITY_DISPLAY.get(str(s)) or str(s))
        return df
    return _bundle_to_frame(market)


def save_universe(market: str, df: pd.DataFrame) -> Path:
    UNIVERSE_DIR.mkdir(parents=True, exist_ok=True)
    path = UNIVERSE_DIR / f'{market}_universe.csv'
    df.to_csv(path, index=False)
    load_universe.cache_clear()
    return path
