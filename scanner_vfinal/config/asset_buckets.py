from __future__ import annotations

US_BUCKETS = {
    "AAPL": "quality_growth",
    "MSFT": "quality_growth",
    "NVDA": "semis_beta",
    "AMZN": "consumer_cyc",
    "GOOG": "quality_growth",
    "GOOGL": "quality_growth",
    "META": "quality_growth",
    "TSLA": "high_beta",
    "XOM": "energy",
    "CVX": "energy",
    "JPM": "financials",
    "IWM": "small_beta",
}
IHSG_BUCKETS = {
    "BBCA.JK": "banks",
    "BBRI.JK": "banks",
    "BMRI.JK": "banks",
    "TLKM.JK": "telco_defensive",
    "ASII.JK": "cyclical",
    "ANTM.JK": "metals_energy",
    "MDKA.JK": "metals_energy",
    "ADRO.JK": "energy_exporter",
}
FOREX_BUCKETS = {
    "EURUSD=X": "usd_major",
    "GBPUSD=X": "usd_major",
    "JPY=X": "jpy_safe_haven",
    "AUDUSD=X": "commodity_fx",
    "NZDUSD=X": "commodity_fx",
    "CAD=X": "commodity_fx",
    "CHF=X": "safe_haven_fx",
    "EURJPY=X": "carry_beta",
    "GBPJPY=X": "carry_beta",
    "IDR=X": "em_fx",
}
COMMODITY_BUCKETS = {
    "GC=F": "precious",
    "SI=F": "precious",
    "CL=F": "energy",
}
CRYPTO_KEYWORD_BUCKETS = {
    "btc": "btc_quality",
    "eth": "majors",
    "sol": "majors",
    "link": "infra",
    "render": "ai_data",
    "fet": "ai_data",
    "tao": "ai_data",
    "ondo": "defi",
    "mkr": "defi",
    "doge": "meme_beta",
    "pepe": "meme_beta",
    "wif": "meme_beta",
}

def bucket_for(market: str, symbol: str, name: str = "") -> str:
    market = market.lower()
    if market == "us":
        return US_BUCKETS.get(symbol, "other_us")
    if market == "ihsg":
        return IHSG_BUCKETS.get(symbol, "other_ihsg")
    if market == "forex":
        return FOREX_BUCKETS.get(symbol, "other_fx")
    if market == "commodities":
        return COMMODITY_BUCKETS.get(symbol, "other_commodity")
    text = f"{symbol} {name}".lower()
    for key, bucket in CRYPTO_KEYWORD_BUCKETS.items():
        if key in text:
            return bucket
    return "other_crypto"
