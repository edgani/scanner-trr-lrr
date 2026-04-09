from __future__ import annotations
from typing import Dict


def infer_theme(symbol: str) -> str:
    if symbol.endswith(".JK"):
        if symbol in {"ADRO.JK", "PTBA.JK", "ITMG.JK", "MEDC.JK", "BUMI.JK", "ANTM.JK", "INCO.JK", "MDKA.JK", "TINS.JK"}:
            return "Resource EM"
        return "IHSG Domestic"
    if symbol in {"GC=F", "SI=F"}:
        return "Gold / hard asset"
    if symbol in {"CL=F", "BZ=F", "NG=F"}:
        return "Energy instrument"
    if symbol in {"HG=F"}:
        return "Industrial metals"
    if symbol in {"XOM", "CVX", "SLB", "HAL", "BKR", "STNG", "FRO", "TNK", "DHT"}:
        return "Energy / shipping"
    if symbol in {"PLTR", "NVDA", "SMCI", "SNDK"}:
        return "AI / compute"
    if symbol in {"TAO22974-USD", "RENDER-USD", "FET-USD"}:
        return "AI / crypto infra"
    if symbol in {"ONDO-USD", "MKR-USD", "LINK-USD"}:
        return "Crypto infrastructure"
    if symbol.endswith("-USD"):
        return "Crypto beta"
    if symbol.endswith("=X"):
        return "FX"
    return "General"


def build_narrative_features(symbol: str) -> Dict[str, float]:
    theme = infer_theme(symbol)
    cluster_score = {
        "Energy / shipping": 0.72,
        "Energy instrument": 0.70,
        "Gold / hard asset": 0.67,
        "Industrial metals": 0.66,
        "AI / compute": 0.68,
        "AI / crypto infra": 0.69,
        "Crypto infrastructure": 0.66,
        "Crypto beta": 0.60,
        "Resource EM": 0.65,
        "IHSG Domestic": 0.56,
        "FX": 0.55,
        "General": 0.50,
    }.get(theme, 0.50)
    return {"theme": theme, "narrative_cluster": cluster_score}
