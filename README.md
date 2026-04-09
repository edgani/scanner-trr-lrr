# Market Intel Final Clean

This pack contains:
- `macroregime_pro/` — macro backbone, no-cut local history store, snapshot-first runtime
- `scanner_pro/` — scanner-first app, horizon-based tabs, hidden macro overlay, snapshot-only runtime

## Quick start
```bash
python verify_all.py
python build_final_snapshots.py
```

Run apps:
```bash
cd macroregime_pro && streamlit run app.py
cd scanner_pro && streamlit run app.py
```

## Important
This code is built to stay light **at runtime**:
- apps read snapshots only
- full-universe refresh and no-cut history update happen in scripts
- nothing heavy runs on page load
