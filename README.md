# CSV Log Analyzer

Kleines Python-CLI zum Auswerten von CSV-Log-Dateien aus dem Terminal. Das Skript liest die gewuenschten Datensaetze ein, erstellt Plots als PNG und gibt einfache Kennzahlen in der Konsole aus.

## Features

- Auswahl der auszuwertenden CSV-Dateien per Kommandozeilenargument
- Auswahl von `system-name`, `record-type` und beliebigen CSV-Spalten
- Auswahl eines Zeitfensters ueber Start- und Endzeit
- Automatische Nachinstallation von `matplotlib` beim ersten Start
- PNG-Ausgabe in `output`
- Konsolenausgabe mit `min`, `max` und `mean` je Spalte
- Zweites CLI zum Finden von Schwellwert-Ueber- und -Unterschreitungen
- technische Dokumentation der Modul-Abhaengigkeiten unter `docs/`

## Voraussetzungen

- Python 3.10 oder neuer
- `pip` verfuegbar im Python-Environment

## Dokumentation

Fuer spaetere Wartung gibt es zusaetzliche Projektdokumentation:

- [Projektstruktur](docs/project_structure.md)
- [Funktions-Abhaengigkeiten](docs/function_dependencies.md)

## Aufruf

### Interaktiver Plotter

Fuer eine grafische Auswahl von CSV-Datei, Datensatz und Spalten:

```powershell
python .\main\csv_plotter.py
```

Das Tool bietet:

- Dateiauswahl fuer beliebige CSV-Dateien
- Drag & Drop von CSV-Dateien direkt auf das Plotter-Fenster
- Unterstuetzung fuer das bisherige APS/APU-Mehrblockformat
- Unterstuetzung fuer normale CSV-Dateien mit einer Header-Zeile
- automatische Erkennung einer Zeitspalte bei Standard-CSV-Dateien
- waehlbare X-Achse bei allen CSV-Dateien: Zeilennummer oder beliebige CSV-Spalte
- Auswahl von `Record Type` und `System` bei APS/APU-Dateien
- Auswahl der vorhandenen numerischen Spalten
- interaktiven Plot mit Toolbar fuer Zoom, Pan, Reset und Speichern
- Mausrad-Zoom direkt auf die aktuelle Cursor-Position
- Verschieben des Plot-Ausschnitts mit gedrueckter mittlerer Maustaste
- Data-Picker per Linksklick auf den Plot: der naechste Messpunkt wird markiert und mit X-/Y-Wert angezeigt
- CSV-Export des aktuell zusammengestellten Plots ueber `Datei > Export`
- Light- und Dark-Mode ueber `Ansicht`
- X-Achse mit Datum und Uhrzeit

Bedienung im Plot:

- `Mausrad`: zoomt immer auf die Position des Mauszeigers, unabhaengig vom Toolbar-Modus
- `Mittlere Maustaste ziehen`: verschiebt den sichtbaren Plot-Ausschnitt
- `Linksklick`: zeigt den naechstgelegenen Messpunkt als Marker, Tooltip und Statuszeilentext
- `Toolbar`: bietet zusaetzlich die Matplotlib-Standardfunktionen wie Home, Back, Forward, Zoom, Pan und Speichern

CSV-Export im GUI:

- `Datei > Export > Gesamten Plot exportieren`: exportiert alle aktuell geplotteten Datenpunkte
- `Datei > Export > Sichtbaren Ausschnitt exportieren`: exportiert nur Datenpunkte innerhalb der aktuellen X- und Y-Achsengrenzen
- Die Export-CSV enthaelt die aktuelle X-Achse als erste Spalte und danach alle aktuell geplotteten Y-Spalten.

Fuer Standard-CSV-Dateien gilt:

- die erste Zeile wird als Header interpretiert
- plottbar sind alle Spalten, die numerische Werte enthalten
- erkannte Zeitspalten koennen z. B. `timestamp`, `time`, `datetime`, `date`, `Datum` oder `Zeit` heissen
- die X-Achse kann auf `Zeilennummer`, eine Zeitspalte, eine numerische Spalte oder eine Textspalte gesetzt werden

Fuer APS/APU-Dateien gilt:

- `Record Type` und `System` waehlen weiter den Datenblock aus
- die X-Achse kann auf `Zeilennummer`, `TimeStamp` oder eine beliebige Spalte des gewaehlten Record Types gesetzt werden

### Plot-Analyse

Aus dem Projektverzeichnis:

```powershell
python .\main\log_analyzer.py .\APS-001249_20260424_000000.csv
```

Mehrere Dateien gleichzeitig:

```powershell
python .\main\log_analyzer.py `
  .\APS-001249_20260424_000000.csv `
  .\APS-001249_20260425_000000.csv
```

Mit anderen Spalten oder anderem Zielsystem:

```powershell
python .\main\log_analyzer.py `
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
python .\main\peak_finder.py `
  .\APS-001249_20260424_000000.csv `
  --columns "VL12/V" "VL23/V" "VL31/V" `
  --threshold-low 620 `
  --threshold-high 650 `
  --time-start "2026-04-24 08:00:00" `
  --time-end "2026-04-24 12:00:00"
```

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
output
```
