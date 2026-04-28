# Installation fuer `csv_plotter.py`

Diese Anleitung gilt fuer Windows mit PowerShell.

## Benoetigt

- Python 3.10 oder neuer
- `pip`
- `matplotlib`
- `tkinter`

Hinweis:
`tkinter` wird normalerweise zusammen mit Python installiert. Wenn du Python ueber den offiziellen Windows-Installer oder ueber `winget` installierst, ist es in der Regel bereits dabei.

## 1. Python installieren

Wenn Python noch nicht installiert ist:

```powershell
winget install Python.Python.3.13
```

Danach PowerShell neu oeffnen und pruefen:

```powershell
python --version
pip --version
```

## 2. `matplotlib` installieren

Im Projektverzeichnis oder allgemein im aktiven Python-Environment:

```powershell
python -m pip install matplotlib
```

## 3. `tkinter` pruefen

Pruefen, ob `tkinter` verfuegbar ist:

```powershell
python -c "import tkinter; print('tkinter ok')"
```

Wenn dabei ein Fehler kommt, ist meist nicht `pip` das Problem, sondern die Python-Installation enthaelt kein Tcl/Tk. Dann Python neu installieren und darauf achten, dass die Standardkomponenten mitinstalliert werden.

## 4. Plotter starten

Aus dem Projektverzeichnis:

```powershell
python .\plotter\csv_plotter.py
```

## Kurzfassung

Wenn Python schon installiert ist, reicht normalerweise:

```powershell
python -m pip install matplotlib
python .\plotter\csv_plotter.py
```
