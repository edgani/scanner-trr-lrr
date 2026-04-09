from __future__ import annotations

from typing import Any, TypedDict


class MarketSection(TypedDict, total=False):
    macro_vs_market: dict[str, Any]
    transmission: dict[str, Any]
    setups_now: list[dict[str, Any]]
    forward_radar: list[dict[str, Any]]
    market_hub: dict[str, Any]
    strong_weak: dict[str, Any]
    execution: dict[str, Any]


class Snapshot(TypedDict, total=False):
    meta: dict[str, Any]
    shared_core: dict[str, Any]
    dashboard: dict[str, Any]
    us: MarketSection
    ihsg: MarketSection
    fx: MarketSection
    commodities: MarketSection
    crypto: MarketSection
    scenarios: dict[str, Any]
    cross_asset: dict[str, Any]
    diagnostics: dict[str, Any]
