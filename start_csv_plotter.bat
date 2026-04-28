@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv" (
    py -m venv .venv
    if errorlevel 1 goto :error
)

call .venv\Scripts\activate.bat
if errorlevel 1 goto :error

python -m pip install --upgrade pip
if errorlevel 1 goto :error

python -m pip install -r requirements.txt
if errorlevel 1 goto :error

python main\csv_plotter.py
if errorlevel 1 goto :error

exit /b 0

:error
echo.
echo Fehler beim Starten des CSV Plotters. Bitte die Ausgabe oben pruefen.
pause
exit /b 1
