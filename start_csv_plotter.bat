@echo off
cd /d "%~dp0"

if not exist ".venv" (
    py -m venv .venv
)

call .venv\Scripts\activate.bat

python -m pip install --upgrade pip

python main\csv_plotter.py