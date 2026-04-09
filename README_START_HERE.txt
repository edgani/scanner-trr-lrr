FINAL WORKFLOW

1) Export scanner brain from MacroRegime v33 cache:
   python -m export_scanner_brain
2) Refresh universes + histories + snapshots locally/VPS:
   python build_daily_local.py
3) Run scanner:
   streamlit run scanner_vfinal/app.py

This pack is architected for local/VPS building and a snapshot-only Streamlit app.
