from __future__ import annotations

from typing import Any

from config.settings import UNIVERSE_MANIFESTS_ENABLED, UNIVERSE_MANIFEST_PREFERRED
from data.universe_manifest_store import load_universe_manifest, manifest_symbols, manifest_summary

US_CURATED_BACKEND_UNIVERSE = {
    "macro_anchors": ["SPY","QQQ","IWM","RSP","TLT","HYG","UUP","EEM","^VIX"],
    "sector_etfs": ["XLE","XLF","XLI","XLB","XLK","XLV","XLY","XLP","XLU","XLRE","XLC"],
    "style_etfs": ["VUG","VTV","QUAL","MTUM","USMV","SPHB","IWD","IWF"],
    "stocks_core": ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AVGO","AMD","NFLX","ORCL","CRM","NOW","ADBE","INTU","PANW","ANET","AMAT","MU","QCOM","TXN","INTC","JPM","BAC","WFC","GS","MS","BLK","KKR","BX","SCHW","HOOD","COIN","V","MA","PYPL","XOM","CVX","COP","SLB","HAL","BKR","OXY","DVN","EOG","KMI","WMB","OKE","FCX","NEM","GOLD","CAT","DE","GE","LMT","NOC","RTX","BA","UNP","CSX","NSC","LLY","UNH","JNJ","MRK","ABBV","PFE","ISRG","ABT","TMO","MDT","WMT","COST","PG","KO","PEP","MCD","UBER","BKNG","CMG","HD","LOW","TGT","NKE","DIS","ROST","TJX","ETSY","LEN","DHI","PHM","PLTR","SMCI","MSTR","SNOW","SHOP","SQ","AFRM","TTD","RDDT","ARM","ASML","KLAC","LRCX","CDNS","SNPS"]
}
IHSG_CURATED_BACKEND_UNIVERSE = {
    "heavyweights": ["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","TLKM.JK","ASII.JK"],
    "banks": ["BRIS.JK","BNGA.JK","BBTN.JK","BTPS.JK","NISP.JK","MEGA.JK"],
    "resources": ["ADRO.JK","PTBA.JK","ITMG.JK","HRUM.JK","INDY.JK","AADI.JK","UNTR.JK","BUMI.JK","PGEO.JK","MEDC.JK","AKRA.JK"],
    "metals": ["ANTM.JK","INCO.JK","MDKA.JK","TINS.JK","BRMS.JK","DKFT.JK"],
    "consumer_defensives": ["ICBP.JK","INDF.JK","MYOR.JK","KLBF.JK","SIDO.JK","CMRY.JK","ULTJ.JK"],
    "consumer_cyclicals": ["AMRT.JK","ACES.JK","MAPI.JK","ERAA.JK"],
    "infra_transport": ["JSMR.JK","PGAS.JK","EXCL.JK","ISAT.JK","WIKA.JK","PTPP.JK","ADHI.JK","SMDR.JK","TMAS.JK"],
    "property_healthcare": ["CTRA.JK","BSDE.JK","PWON.JK","SMRA.JK","HEAL.JK","MIKA.JK","SILO.JK"],
    "extra_liquid": ["CPIN.JK","JPFA.JK","INKP.JK","TKIM.JK","ESSA.JK","AALI.JK","LSIP.JK","MAPA.JK","AUTO.JK"]
}
FX_CURATED_BACKEND_UNIVERSE = ["EURUSD=X","GBPUSD=X","AUDUSD=X","NZDUSD=X","JPY=X","CHF=X","CAD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","NZDJPY=X","EURGBP=X","EURCHF=X","IDR=X","CNH=X","SGD=X"]
COMMODITIES_CURATED_BACKEND_UNIVERSE = {"precious":["GC=F","SI=F","PL=F","PA=F"],"energy":["CL=F","BZ=F","NG=F","RB=F","HO=F"],"industrial_metals":["HG=F"],"agri_softs":["ZC=F","ZW=F","ZS=F","KC=F","SB=F","CT=F","CC=F","LE=F","HE=F"],"broad_proxies":["DBC","GSG","DBA","DBB","URA"]}
CRYPTO_CURATED_BACKEND_UNIVERSE = {"majors":["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","ADA-USD","AVAX-USD","LINK-USD","DOT-USD","DOGE-USD"],"l1_l2":["ATOM-USD","NEAR-USD","APT-USD","ARB-USD","OP-USD","MATIC-USD","SUI20947-USD"],"defi":["AAVE-USD","UNI7083-USD","MKR-USD","LDO-USD","CRV-USD","COMP5692-USD"],"ai_data":["FET-USD","TAO22974-USD","RNDR-USD","RENDER-USD","GRT6719-USD"],"rwa":["ONDO-USD","POLYX-USD"],"infra":["TON11419-USD","INJ-USD","SEI-USD","TIA22861-USD","PYTH-USD"],"high_beta":["WIF-USD","PEPE24478-USD","BONK-USD","FLOKI-USD","BRETT-USD"]}


def flatten_symbols(obj) -> list[str]:
    out: list[str] = []

    def _walk(node):
        if isinstance(node, dict):
            for value in node.values():
                _walk(value)
            return
        if isinstance(node, (list, tuple, set)):
            for value in node:
                _walk(value)
            return
        sym = str(node).strip()
        if sym and sym not in out:
            out.append(sym)

    _walk(obj)
    return out


def unique_symbols(*parts) -> list[str]:
    out: list[str] = []
    for part in parts:
        for sym in flatten_symbols(part):
            if sym not in out:
                out.append(sym)
    return out


def _manifest_list(market: str) -> list[str]:
    if not (UNIVERSE_MANIFESTS_ENABLED and UNIVERSE_MANIFEST_PREFERRED):
        return []
    return manifest_symbols(load_universe_manifest(market))


def _choose_backend(market: str, curated: Any):
    manifest_list = _manifest_list(market)
    return manifest_list if manifest_list else curated


US_BACKEND_UNIVERSE = _choose_backend('us', US_CURATED_BACKEND_UNIVERSE)
IHSG_BACKEND_UNIVERSE = _choose_backend('ihsg', IHSG_CURATED_BACKEND_UNIVERSE)
FX_BACKEND_UNIVERSE = _choose_backend('fx', FX_CURATED_BACKEND_UNIVERSE)
COMMODITIES_BACKEND_UNIVERSE = _choose_backend('commodities', COMMODITIES_CURATED_BACKEND_UNIVERSE)
CRYPTO_BACKEND_UNIVERSE = _choose_backend('crypto', CRYPTO_CURATED_BACKEND_UNIVERSE)


def get_market_ranking_universe(*parts) -> list[str]:
    return unique_symbols(*parts)


def build_coverage_report(primary, backend) -> dict:
    bucket_symbols = flatten_symbols(primary)
    backend_symbols = flatten_symbols(backend)
    ranking_symbols = unique_symbols(primary, backend)
    bucket_set = set(bucket_symbols)
    backend_set = set(backend_symbols)
    return {
        'bucket_universe_size': len(bucket_symbols),
        'backend_universe_size': len(backend_symbols),
        'ranking_universe_size': len(ranking_symbols),
        'unbucketed_symbols': [sym for sym in backend_symbols if sym not in bucket_set],
        'bucket_only_symbols': [sym for sym in bucket_symbols if sym not in backend_set],
        'missing_from_ranking': [sym for sym in unique_symbols(primary, backend) if sym not in ranking_symbols],
    }


def build_manifest_repo() -> dict[str, dict]:
    repo = {}
    for market in ('us', 'ihsg', 'crypto', 'fx', 'commodities'):
        payload = load_universe_manifest(market)
        repo[market] = manifest_summary(payload) if payload else {'market': market, 'count': 0, 'source': None, 'generated_at': None, 'stats': {}, 'has_records': False}
    return repo
