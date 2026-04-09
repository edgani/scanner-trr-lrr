@echo off
setlocal
python -m pip install --upgrade pip
pip install -r requirements-all.txt
python build_daily_local.py
pause
