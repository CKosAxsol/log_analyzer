@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="

where py >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD (
    echo Python wurde nicht gefunden. Installation ueber winget wird gestartet...
    where winget >nul 2>nul
    if errorlevel 1 (
        echo winget wurde nicht gefunden. Bitte Python 3.10 oder neuer manuell installieren:
        echo https://www.python.org/downloads/windows/
        goto :error
    )

    winget install -e --id Python.Python.3.12
    if errorlevel 1 goto :error

    where py >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3"
    )
)

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD (
    echo Python wurde installiert, ist in diesem Terminal aber noch nicht im PATH verfuegbar.
    echo Bitte dieses Fenster schliessen und start_csv_plotter.bat erneut ausfuehren.
    goto :error
)

if not exist ".venv" (
    %PYTHON_CMD% -m venv .venv
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
