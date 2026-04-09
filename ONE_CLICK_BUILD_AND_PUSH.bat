@echo off
setlocal
python -m pip install --upgrade pip
pip install -r requirements-all.txt
python auto_build_and_push.py
pause
