@echo off
cd /d "%~dp0"
python -m pip install -r requirements-all.txt
python verify_all.py
python build_everything_full.py
pause
