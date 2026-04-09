from __future__ import annotations

import os

APP_NAME = "MacroRegime Pro"
APP_VERSION = "0.33.0-final-route-aware-full-manifests-light-runtime"

# Historical storage policy
DEFAULT_PRICE_PERIOD = "max"
DEFAULT_LOOKBACK_DAYS = 252
DEFAULT_REFRESH_PERIOD = "3mo"
MAX_PAGE_UNIVERSE = 36

# Runtime / storage
CACHE_BASE_DIR = ".cache"
SNAPSHOT_FILENAME = "latest_snapshot.json"
SNAPSHOT_MANIFEST_FILENAME = "latest_snapshot_manifest.json"
HISTORY_DIRNAME = "history"
HISTORY_META_FILENAME = "history_manifest.json"
PRICE_CACHE_TTL_SECONDS = 300
FRED_CACHE_TTL_SECONDS = 1800
NEWS_CACHE_TTL_SECONDS = 900
EVENT_CACHE_TTL_SECONDS = 1800
SNAPSHOT_SCHEMA = "v33.0-final-route-aware-full-manifests-light-runtime"
LIVE_RUNTIME_MODE = "snapshot_only"
LIVE_FETCH_ENABLED = os.getenv('MRP_LIVE_FETCH', '1').strip().lower() not in {'0', 'false', 'no', 'off'}

# Price updater defaults
PRICE_UPDATE_BATCH_SIZE = 12
PRICE_FULL_BOOTSTRAP_PERIOD = "max"
PRICE_INCREMENTAL_REFRESH_PERIOD = "3mo"
PRICE_MIN_HISTORY_POINTS = 60


# Universe manifest / full-universe controls
UNIVERSE_DIRNAME = 'universe'
UNIVERSE_MANIFESTS_ENABLED = os.getenv('MRP_UNIVERSE_MANIFESTS', '1').strip().lower() not in {'0', 'false', 'no', 'off'}
UNIVERSE_MANIFEST_PREFERRED = os.getenv('MRP_UNIVERSE_MANIFEST_PREFERRED', '1').strip().lower() not in {'0', 'false', 'no', 'off'}
COINGECKO_DEMO_API_KEY = os.getenv('COINGECKO_DEMO_API_KEY', '').strip()
COINGECKO_PRO_API_KEY = os.getenv('COINGECKO_PRO_API_KEY', '').strip()
COINGECKO_API_BASE = 'https://pro-api.coingecko.com/api/v3' if COINGECKO_PRO_API_KEY else 'https://api.coingecko.com/api/v3'
COINGECKO_HISTORY_DAYS = os.getenv('MRP_COINGECKO_HISTORY_DAYS', 'max').strip() or 'max'
COINGECKO_MARKETS_VS_CURRENCY = os.getenv('MRP_COINGECKO_VS_CURRENCY', 'usd').strip().lower() or 'usd'

# Prior control for the Quad engine.
# off    -> fully non-anchored
# gentle -> minimal structural nudge when coverage is weak
# strong -> preserve prior project behavior more closely
REGIME_PRIOR_MODE = "off"

REGIME_PRIOR_MAP = {
    "off": {"Q1": 0.00, "Q2": 0.00, "Q3": 0.00, "Q4": 0.00},
    "gentle": {"Q1": 0.00, "Q2": 0.00, "Q3": 0.03, "Q4": 0.00},
    "strong": {"Q1": -0.05, "Q2": 0.00, "Q3": 0.10, "Q4": -0.02},
}

# Backward-compatible alias.
REGIME_PRIOR = REGIME_PRIOR_MAP[REGIME_PRIOR_MODE]


def get_regime_prior(mode: str | None = None) -> dict[str, float]:
    selected = mode or REGIME_PRIOR_MODE
    return dict(REGIME_PRIOR_MAP.get(selected, REGIME_PRIOR_MAP["off"]))


def get_prior_strength(data_coverage: float, mode: str | None = None) -> float:
    selected = mode or REGIME_PRIOR_MODE
    coverage = max(0.0, min(1.0, float(data_coverage)))
    if selected == "off":
        return 0.0
    if selected == "gentle":
        return 0.10 + 0.10 * (1.0 - coverage)
    if selected == "strong":
        return 0.35 + 0.20 * (1.0 - coverage)
    return 0.0
