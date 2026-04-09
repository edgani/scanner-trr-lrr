from __future__ import annotations

def _state(score: float) -> tuple[str, str]:
    if score >= 0.67: return "Improving", "good"
    if score >= 0.45: return "Mixed", "warn"
    return "Fragile", "bad"

def build_global_checklist(shared_core: dict, features: dict, news_state: dict, em_rotation: dict) -> list[dict]:
    macro=features["macro"]; market=features["market"]
    items=[("Growth",0.5+0.5*float(macro.get("growth_momentum",0.0))),("Inflasi",0.5-0.35*float(macro.get("inflation_shock",0.0))),("DXY",0.5-0.5*max(0.0,float(market.get("dxy_1m",0.0)))),("Yields",0.5+0.5*float(market.get("tlt_1m",0.0))),("Breadth",float(market.get("breadth_health",0.5))),("Vol/Credit",0.6 if shared_core.get("vix_bucket",{}).get("bucket") in {"calm","normal"} else 0.3),("Liquidity",0.55 if shared_core.get("execution_mode",{}).get("mode") != "defensive" else 0.35),("Geopolitics",0.65 if str(news_state.get("state","quiet")) in {"quiet","relief"} else 0.35),("EM Rotation",float(em_rotation.get("score",0.4))),("Event/News",0.65 if str(news_state.get("state","quiet")) in {"quiet","relief"} else 0.4)]
    out=[]
    for label,score in items:
        state,tone=_state(max(0.0,min(1.0,float(score)))); out.append({"label":label,"score":float(score),"state":state,"tone":tone})
    return out

def build_asset_checklists(shared_core: dict, native_features: dict) -> dict:
    return {"us":_build_us(native_features.get("us",{})),"ihsg":_build_ihsg(native_features.get("ihsg",{})),"fx":_build_fx(native_features.get("fx",{})),"commodities":_build_commodities(native_features.get("commodities",{})),"crypto":_build_crypto(native_features.get("crypto",{}))}

def _wrap(items):
    out=[]
    for label,score in items:
        state,tone=_state(max(0.0,min(1.0,float(score)))); out.append({"label":label,"score":float(score),"state":state,"tone":tone})
    return out

def _build_us(f):
    return _wrap([("Breadth melebar",f.get("breadth_health",0.5)),("Equal-weight confirm",f.get("eqw_health",0.5)),("Small caps ikut",f.get("smallcap_health",0.5)),("Credit aman",f.get("credit_ok",0.5)),("Vol mendukung",f.get("vol_ok",0.5)),("Sector breadth sehat",f.get("sector_breadth_score",0.5))])

def _build_ihsg(f):
    return _wrap([("USD/IDR aman",1-f.get("usd_idr_pressure",0.5)),("SBN yield aman",1-f.get("indo_yield_pressure",0.5)),("Foreign flow confirm",f.get("foreign_flow",0.5)),("Breadth confirm",f.get("breadth_liquidity",0.5)),("Heavyweights sehat",f.get("heavyweights",0.5)),("Banks/resources confirm",0.5*(f.get("bank_health",0.5)+f.get("commodity_spillover",0.5)))])

def _build_fx(f):
    return _wrap([("Rate diff bersih",f.get("rate_diff",0.5)),("Macro surprise confirm",f.get("macro_surprise_diff",0.5)),("Positioning dingin",1-f.get("positioning_heat",0.5)),("Options nggak ekstrem",1-f.get("options_heat",0.5)),("Liquidity oke",f.get("liquidity_quality",0.5)),("Intervention risk rendah",1-f.get("intervention_risk",0.5))])

def _build_commodities(f):
    return _wrap([("Physical balance ketat",f.get("physical_balance",0.5)),("Inventory tipis",f.get("inventory_stress",0.5)),("Curve confirm",f.get("curve_tightness",0.5)),("USD/rates mendukung",1-f.get("usd_rates_pressure",0.5)),("Shock supply/logistics",f.get("exogenous_shock",0.5)),("Positioning nggak kepanasan",1-f.get("positioning_vol",0.5))])

def _build_crypto(f):
    return _wrap([("Flow masuk",f.get("flow",0.5)),("Funding/OI sehat",1-f.get("leverage_heat",0.5)),("Unlock aman",1-f.get("supply_overhang",0.5)),("Usage naik",f.get("usage",0.5)),("Liquidity cukup",1-f.get("liquidity_fragility",0.5)),("Narrative hidup",f.get("narrative",0.5))])
