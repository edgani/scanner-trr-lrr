from __future__ import annotations

from functools import lru_cache
from typing import Any

from config.asset_buckets import US_BUCKETS, IHSG_BUCKETS, FX_BUCKETS, COMMODITY_BUCKETS, CRYPTO_BUCKETS
from data.universe_manifest_store import load_universe_manifest


def _invert(bucket_map: dict[str, list[str]], mapping: dict[str, str]) -> dict[str, str]:
    for bucket, syms in (bucket_map or {}).items():
        for sym in syms:
            mapping[str(sym).strip()] = bucket
    return mapping


_US_BUCKET_TO_FAMILY = {
    'Growth': 'growth',
    'Quality': 'quality',
    'Defensives': 'defensives',
    'Semis': 'semis',
    'Software/Cyber': 'software_cyber',
    'Energy': 'energy',
    'Industrials': 'industrials',
    'Brokers/Alt': 'brokers_alt',
}
_IHSG_BUCKET_TO_FAMILY = {
    'Banks': 'banks',
    'Coal/Energy': 'coal_energy',
    'Metals': 'metals',
    'Telco/Infra': 'telco_infra',
    'Consumer Def': 'consumer_def',
    'Consumer Cyc': 'consumer_cyc',
    'Property/Health': 'property_health',
}
_FX_BUCKET_TO_FAMILY = {
    'Majors': 'majors',
    'JPY Crosses': 'carry_beta',
    'Core Crosses': 'majors',
    'Asia Overlay': 'asia_beta',
}
_COM_BUCKET_TO_FAMILY = {
    'Precious': 'precious',
    'Energy': 'energy',
    'Industrial': 'industrial',
    'Agri/Softs': 'agri_softs',
    'Livestock': 'agri_softs',
    'Broad Proxies': 'broad_proxy',
}
_CRYPTO_BUCKET_TO_FAMILY = {
    'Majors': 'majors',
    'L1/L2': 'l1l2',
    'DeFi': 'defi',
    'AI/Data': 'ai_data',
    'RWA': 'rwa',
    'Infra': 'infra',
    'High Beta': 'high_beta',
}

_SYMBOL_TO_BUCKET: dict[str, dict[str, str]] = {
    'us': _invert(US_BUCKETS, {}),
    'ihsg': _invert(IHSG_BUCKETS, {}),
    'fx': _invert(FX_BUCKETS, {}),
    'commodities': _invert(COMMODITY_BUCKETS, {}),
    'crypto': _invert(CRYPTO_BUCKETS, {}),
}


@lru_cache(maxsize=8)
def _manifest_records(market: str) -> dict[str, dict[str, Any]]:
    payload = load_universe_manifest(market)
    out: dict[str, dict[str, Any]] = {}
    for row in payload.get('records', []) or []:
        if isinstance(row, dict):
            sym = str(row.get('symbol', '')).strip()
            if sym:
                out[sym] = row
    return out


def manifest_record(market: str, symbol: str) -> dict[str, Any]:
    return _manifest_records(market).get(str(symbol).strip(), {}) or {}


def _name_text(market: str, symbol: str) -> str:
    rec = manifest_record(market, symbol)
    txt = ' '.join(str(rec.get(k, '')) for k in ('name', 'raw_symbol', 'coin_id', 'listing_board')).strip().lower()
    return txt


def classify_symbol(market: str, symbol: str) -> tuple[str, set[str]]:
    m = str(market).lower().strip()
    sym = str(symbol).strip()
    bucket = _SYMBOL_TO_BUCKET.get(m, {}).get(sym)
    traits: set[str] = set()
    if m == 'us' and bucket:
        return _US_BUCKET_TO_FAMILY.get(bucket, 'unclassified'), traits
    if m == 'ihsg' and bucket:
        fam = _IHSG_BUCKET_TO_FAMILY.get(bucket, 'unclassified')
        rec = manifest_record(m, sym)
        board = str(rec.get('listing_board', '')).lower()
        if 'pemantauan' in board:
            traits.add('special_board')
        if fam in {'coal_energy', 'metals'}:
            traits.add('exporter')
        if fam == 'consumer_cyc':
            traits.add('import_sensitive')
        if sym in {'BBCA.JK', 'BBRI.JK', 'BMRI.JK', 'TLKM.JK'}:
            traits.add('quality_largecap')
        return fam, traits
    if m == 'fx' and bucket:
        fam = _FX_BUCKET_TO_FAMILY.get(bucket, 'majors')
        if sym in {'JPY=X', 'CHF=X', 'EURUSD=X', 'SGD=X'}:
            traits.add('defensive_usd')
        if sym in {'AUDUSD=X', 'NZDUSD=X', 'CAD=X'}:
            traits.add('commodity_fx')
        return fam, traits
    if m == 'commodities' and bucket:
        return _COM_BUCKET_TO_FAMILY.get(bucket, 'unclassified'), traits
    if m == 'crypto' and bucket:
        fam = _CRYPTO_BUCKET_TO_FAMILY.get(bucket, 'unclassified')
        if sym == 'BTC-USD' or sym == 'CG:bitcoin':
            fam = 'btc_quality'
        if fam == 'high_beta':
            traits.add('meme_beta')
        return fam, traits

    text = _name_text(m, sym)

    if m == 'us':
        rec = manifest_record(m, sym)
        if rec.get('is_etf'):
            traits.add('etf')
            return 'broad_etf', traits
        if any(k in text for k in (' warrant', ' warrants', ' right', ' rights', ' unit', ' units')):
            traits.add('junk_structure')
            return 'junk_structure', traits
        if any(k in text for k in ('acquisition', 'blank check', 'spac')):
            traits.add('junk_structure')
            return 'junk_structure', traits
        if any(k in text for k in ('energy', 'oil', 'gas', 'petroleum', 'uranium')):
            return 'energy', traits
        if any(k in text for k in ('mining', 'gold', 'silver', 'copper', 'steel', 'materials')):
            return 'materials', traits
        if any(k in text for k in ('bank', 'capital', 'financial', 'insurance', 'payments')):
            return 'brokers_alt', traits
        if any(k in text for k in ('software', 'cloud', 'cyber', 'security', 'data', 'ai', 'semiconductor', 'chip')):
            return 'quality_growth', traits
        if any(k in text for k in ('consumer', 'retail', 'restaurant', 'travel', 'hotel', 'leisure')):
            return 'consumer_cyc', traits
        if any(k in text for k in ('pharma', 'health', 'medical', 'utility', 'telecom', 'staples')):
            return 'defensives', traits
        return 'small_beta', traits

    if m == 'ihsg':
        rec = manifest_record(m, sym)
        board = str(rec.get('listing_board', '')).lower()
        if 'pemantauan' in board:
            traits.add('special_board')
        if any(k in text for k in ('bank', 'bca', 'bri', 'mandiri', 'bni')):
            traits.add('quality_largecap')
            return 'banks', traits
        if any(k in text for k in ('coal', 'energy', 'mining', 'gas', 'geothermal', 'oil')):
            traits.add('exporter')
            return 'coal_energy', traits
        if any(k in text for k in ('nickel', 'metal', 'timah', 'emas', 'gold', 'copper')):
            traits.add('exporter')
            return 'metals', traits
        if any(k in text for k in ('telekom', 'tower', 'infra', 'logistik', 'transport', 'shipping', 'pelabuhan')):
            return 'telco_infra', traits
        if any(k in text for k in ('food', 'consumer', 'pharma', 'health', 'clinic', 'hospital')):
            return 'consumer_def', traits
        if any(k in text for k in ('retail', 'automotive', 'property', 'mall', 'store')):
            traits.add('import_sensitive')
            return 'consumer_cyc', traits
        return 'unclassified', traits

    if m == 'fx':
        if sym in {'JPY=X', 'CHF=X', 'EURUSD=X'}:
            traits.add('defensive_usd')
            return 'majors', traits
        if sym in {'AUDUSD=X', 'NZDUSD=X', 'CAD=X'}:
            traits.add('commodity_fx')
            return 'commodity_fx', traits
        if sym in {'IDR=X', 'CNH=X', 'SGD=X'}:
            traits.add('asia_beta')
            return 'asia_beta', traits
        return 'majors', traits

    if m == 'commodities':
        if any(k in sym for k in ('GC', 'SI', 'PL', 'PA')):
            return 'precious', traits
        if any(k in sym for k in ('CL', 'BZ', 'NG', 'RB', 'HO')):
            return 'energy', traits
        if any(k in sym for k in ('HG', 'DBB')):
            return 'industrial', traits
        if any(k in sym for k in ('ZC', 'ZW', 'ZS', 'KC', 'SB', 'CT', 'CC', 'DBA')):
            return 'agri_softs', traits
        return 'broad_proxy', traits

    if m == 'crypto':
        rec = manifest_record(m, sym)
        coin_id = str(rec.get('coin_id', '')).strip().lower()
        raw_symbol = str(rec.get('raw_symbol', '')).strip().upper()
        is_cg = sym.upper().startswith('CG:')
        if any(k in text for k in ('2x', '3x', '5x', '10x', ' leveraged', 'bull ', ' bear', 'short ', ' long ', 'inverse')):
            traits.add('leveraged_token')
            return 'micro_alt', traits
        if sym in {'BTC-USD', 'CG:bitcoin'} or coin_id == 'bitcoin' or (not is_cg and raw_symbol == 'BTC'):
            return 'btc_quality', {'majors'}
        if coin_id in {'ethereum', 'solana', 'binancecoin', 'ripple', 'cardano', 'avalanche-2'} or (not is_cg and raw_symbol in {'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX'}):
            return 'majors', traits
        if coin_id in {'render-token', 'fetch-ai', 'bittensor', 'the-graph'} or (not is_cg and raw_symbol in {'RENDER', 'RNDR', 'FET', 'TAO', 'GRT'}):
            return 'ai_data', traits
        if coin_id in {'aave', 'maker', 'curve-dao-token', 'compound-governance-token', 'lido-dao', 'uniswap'} or (not is_cg and raw_symbol in {'AAVE', 'MKR', 'CRV', 'COMP', 'LDO', 'UNI'}):
            return 'defi', traits
        if coin_id in {'arbitrum', 'optimism', 'matic-network', 'aptos', 'sui', 'near-protocol', 'the-open-network', 'sei-network', 'celestia'} or (not is_cg and raw_symbol in {'ARB', 'OP', 'MATIC', 'APT', 'SUI', 'NEAR', 'TON', 'SEI', 'TIA'}):
            return 'l1l2', traits
        if coin_id in {'ondo-finance', 'polymesh', 'chainlink', 'pyth-network', 'injective-protocol'} or (not is_cg and raw_symbol in {'ONDO', 'POLYX', 'LINK', 'PYTH', 'INJ'}):
            return 'infra', traits
        if coin_id in {'dogecoin', 'pepe', 'bonk', 'floki', 'dogwifcoin'} or (not is_cg and raw_symbol in {'DOGE', 'PEPE', 'BONK', 'FLOKI', 'WIF'}):
            traits.add('meme_beta')
            return 'high_beta', traits
        return 'micro_alt', traits

    return 'unclassified', traits
