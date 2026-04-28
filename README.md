# CSV Voltage Analyzer

Kleines Python-CLI zum Auswerten von APS/APU-CSV-Dateien aus dem Terminal. Das Skript liest die gewuenschten Datensaetze ein, erstellt Spannungsplots als PNG und gibt einfache Kennzahlen in der Konsole aus.

## Features

- Auswahl der auszuwertenden CSV-Dateien per Kommandozeilenargument
- Auswahl von `system-name`, `record-type` und beliebigen CSV-Spalten
- Auswahl eines Zeitfensters ueber Start- und Endzeit
- Automatische Nachinstallation von `matplotlib` beim ersten Start
- PNG-Ausgabe in `scripts/output`
- Konsolenausgabe mit `min`, `max` und `mean` je Spalte
- Zweites CLI zum Finden von Schwellwert-Ueber- und -Unterschreitungen

## Voraussetzungen

- Python 3.10 oder neuer
- `pip` verfuegbar im Python-Environment

## Aufruf

### Plot-Analyse

Aus dem Projektverzeichnis:

```powershell
python .\scripts\log_analyzer.py .\APS-001249_20260424_000000.csv
```

Mehrere Dateien gleichzeitig:

```powershell
python .\scripts\log_analyzer.py `
  .\APS-001249_20260424_000000.csv `
  .\APS-001249_20260425_000000.csv
```

Mit anderen Spalten oder anderem Zielsystem:

```powershell
python .\scripts\log_analyzer.py `
  .\APS-001249_20260424_000000.csv `
  --system-name "APU 2" `
  --record-type "APU Stat 10s" `
  --columns "VL12/V" "VL23/V" "VL31/V" "Vdc/V" `
  --time-start "2026-04-24 08:00:00" `
  --time-end "2026-04-24 12:00:00" `
  --y-min 600 `
  --y-max 700
```

### Schwellwertsuche

Finde Zeitstempel, an denen Spannungen unter `620 V` fallen oder ueber `650 V` steigen:

```powershell
python .\scripts\peak_finder.py `
  .\APS-001249_20260424_000000.csv `
  --columns "VL12/V" "VL23/V" "VL31/V" `
  --threshold-low 620 `
  --threshold-high 650 `
  --time-start "2026-04-24 08:00:00" `
  --time-end "2026-04-24 12:00:00"
```

### Interaktiver Plotter

Fuer eine grafische Auswahl von CSV-Datei, Datensatz und Spalten:

```powershell
python .\plotter\csv_plotter.py
```

Das Tool bietet:

- Dateiauswahl fuer beliebige CSV-Dateien
- Auswahl von `Record Type` und `System`
- Auswahl der vorhandenen numerischen Spalten
- interaktiven Plot mit Toolbar fuer Zoom, Pan und Reset
- X-Achse mit Datum und Uhrzeit

## Wichtige Parameter

- `files`: eine oder mehrere CSV-Dateien
- `--system-name`: z. B. `APU 2`
- `--record-type`: z. B. `APU Stat 10s`
- `--columns`: zu plottende Spalten
- `--output-dir`: Zielordner fuer PNG-Dateien
- `--title`: eigener Plot-Titel
- `--time-start` / `--time-end`: Zeitfenster im Format `YYYY-MM-DD HH:MM:SS`
- `--y-min` / `--y-max`: feste Y-Achse
- `--dpi`: Aufloesung des PNG
- `--delimiter`: CSV-Trennzeichen, standardmaessig `;`

Wichtige Parameter fuer `peak_finder.py`:

- `--threshold-low`: meldet Uebergaenge von `>= threshold` auf `< threshold`
- `--threshold-high`: meldet Uebergaenge von `<= threshold` auf `> threshold`
- `--time-start` / `--time-end`: begrenzt den Suchbereich
- `--columns`: legt fest, welche Spannungsreihen geprueft werden

## Ausgabe

Pro Eingabedatei erzeugt das Tool:

- ein PNG mit dem Spannungsverlauf
- eine kurze Statistik pro Spalte in der Konsole

Standard-Ausgabeordner:

```text
scripts/output
```

## Hinweise fuer GitHub

- Die erzeugten Plot-Dateien sind per `.gitignore` ausgeschlossen.
- Der Ordner kann direkt als kleines CLI-Hilfstool versioniert werden.
