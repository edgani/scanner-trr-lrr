# Scanner Pro Final Clean

Scanner-first project with hidden macro overlay and snapshot-only runtime.

## Core design
- App is **read-only**: it only reads ready snapshots.
- Heavy work happens in scripts:
  - full-universe refresh
  - no-cut history update (`period=max`)
  - snapshot build per market
- Macro stays backend-only and is read from `data/macro/latest_snapshot.json`.

## Markets
- US Stocks: refreshable full universe from Nasdaq Trader
- IHSG: refreshable full universe from IDX page scrape
- Crypto: refreshable full universe from Binance exchange info, then filtered by Yahoo support when histories are updated
- Forex: curated liquid broker-style majors/crosses
- Commodities: `GC=F`, `SI=F`, `CL=F`

## Runtime
The app is intentionally light:
- no yfinance on page load
- no live scan on page load
- no auto-export on page load
- detail is rendered only from snapshot rows

## Build
```bash
python scripts/refresh_universe_snapshots.py --market us
python scripts/refresh_universe_snapshots.py --market ihsg
python scripts/refresh_universe_snapshots.py --market crypto
python scripts/update_full_history.py --market all --force-refresh
python scripts/build_all_snapshots.py
streamlit run app.py
```

## Notes
- Historical data is stored locally per symbol and merged, so history is not intentionally cut.
- Universe completeness depends on what the upstream sources return and what Yahoo Finance actually supports at refresh time.
- Build scripts write manifests with failures so nothing is silently dropped.
