# Lokale Entwicklung

Dieses Dokument beschreibt den einfachsten Weg, das Projekt lokal zu starten und zu pflegen.

## Voraussetzungen

- Python 3.10 oder neuer
- `pip` im aktiven Python-Umfeld
- unter Windows fuer die GUI zusaetzlich eine Python-Installation mit `tkinter`

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements.txt
```

## Wichtige Startbefehle

### Interaktive GUI

```powershell
python .\main\csv_plotter.py
```

### PNG-Analyse im Terminal

```powershell
python .\main\log_analyzer.py .\input\beispiel.csv
```

### Schwellwertsuche

```powershell
python .\main\peak_finder.py .\input\beispiel.csv --threshold-low 620
```

## Arbeitsregeln in diesem Repo

- Bei inhaltlichen Aenderungen soll die passende `README.md` mitgepflegt werden.
- Der Ordner `manifest/` dokumentiert Arbeitsanweisungen und Abhaengigkeiten.
- Komplexere Logik soll moeglichst in kleine Funktionen oder Hilfsmodule ausgelagert werden.
- Neue externe Pakete sollen nur mit klarer Begruendung aufgenommen werden.

## Typische Wartung

- Aendert sich das CSV-Format, zuerst `functions/csv_parser.py` und die GUI-Lader pruefen.
- Aendert sich nur die Darstellung, zuerst `functions/plotting.py` oder die GUI-Plot-Helfer pruefen.
- Aendert sich nur das Verhalten der Kommandozeile, zuerst die Dateien in `main/` und `functions/cli.py` pruefen.
