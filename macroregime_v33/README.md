# MacroRegime Pro v29 — final audit, live-history, snapshot-first

This build hardens the original MacroRegime app for the workflow you asked for:

- live-capable data path for prices and macro inputs
- no 2-year cutoff for stored price history (`max` bootstrap policy)
- snapshot-first app runtime so opening the app stays light
- backend/local history store for full price history per symbol
- explicit loader/history metadata so you can see coverage and staleness

## What changed

### 1. No historical cut
The old default `2y` price window is removed from the storage path.

- initial bootstrap policy: `max`
- incremental refresh policy: `3mo`
- local history store: `.cache/history/*.csv.gz`

The app does **not** need to load all of that history at render time. Full history is stored; the runtime reads the latest snapshot.

### 2. App runtime stays light
The Streamlit app now defaults to **snapshot-first** mode:

- open app -> read latest saved snapshot
- click refresh -> rebuild backend snapshot
- no need to re-fetch full history on every page load

### 3. Backend updater scripts
Use these scripts outside the app when you want to keep the data fresh.

```bash
python scripts/update_full_history.py --markets all --force-refresh
python scripts/build_live_snapshot.py --force-refresh --compact-mode
```

Or do both in one step:

```bash
python scripts/refresh_all.py
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Offline smoke test (optional)
If you want to verify imports/build paths without hitting live endpoints:

```bash
MRP_LIVE_FETCH=0 python scripts/verify_project.py --strict
MRP_LIVE_FETCH=0 python scripts/build_live_snapshot.py --compact-mode
```

## Deploy to Streamlit Community Cloud

Upload this repo to GitHub, then choose:

- Branch: `main`
- Main file path: `app.py`

## Notes

- `MRP_LIVE_FETCH=0` disables external fetches and lets the project boot from local cache/snapshot only.
- The app remains snapshot-first by design so opening it stays light even when the stored history is large.
- Full-universe storage and refresh are backend concerns; the scanner layer can reuse the same history store later.


## Final audit checklist

```bash
# 1) offline structural audit
MRP_LIVE_FETCH=0 python scripts/verify_project.py --strict

# 2) rebuild local snapshot from live/local sources
python scripts/build_live_snapshot.py --force-refresh --compact-mode

# 3) open the UI
streamlit run app.py
```

The strict verifier checks imports, compiles the codebase, builds a snapshot, and validates that every market section exposes the fields the UI expects.


## Clean repo note
This package preserves the existing app/UI while adding backend-only support paths for optional full-universe manifests and crypto `CG:<coin_id>` loading.
No page layout or visual components were intentionally changed.
