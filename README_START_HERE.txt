FIRST: use run_daily_builder.bat (or python build_daily_local.py) on your own machine/VPS.
Then commit the changed snapshot/universe files to GitHub.

START HERE

1) Open terminal in this folder
2) Install deps:
   pip install -r requirements-all.txt

3) Optional verify:
   python verify_all.py

4) Build latest macro + scanner snapshots:
   python build_everything_full.py

5) Run MacroRegime:
   cd macroregime_pro
   streamlit run app.py

6) Run Scanner:
   cd scanner_pro
   streamlit run app.py

Notes:
- Repo/build is snapshot-first, so app stays light on open.
- Full universe is refreshed during build step, not at page load.
- Historical path uses max history where provider supports it.
