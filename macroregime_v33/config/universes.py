from __future__ import annotations
from config.universe_registry import US_BACKEND_UNIVERSE, IHSG_BACKEND_UNIVERSE, FX_BACKEND_UNIVERSE, COMMODITIES_BACKEND_UNIVERSE, CRYPTO_BACKEND_UNIVERSE


def _flatten(obj):
    if isinstance(obj, dict):
        out=[]
        for v in obj.values():
            out.extend(_flatten(v))
        return out
    if isinstance(obj,(list,tuple,set)):
        out=[]
        for v in obj:
            out.extend(_flatten(v))
        return out
    return [str(obj)]

FULL_UNIVERSE=list(dict.fromkeys(["SPY","QQQ","IWM","RSP","TLT","HYG","UUP","EEM","^JKSE","^VIX"]+_flatten(US_BACKEND_UNIVERSE)+_flatten(IHSG_BACKEND_UNIVERSE)+_flatten(FX_BACKEND_UNIVERSE)+_flatten(COMMODITIES_BACKEND_UNIVERSE)+_flatten(CRYPTO_BACKEND_UNIVERSE)))
