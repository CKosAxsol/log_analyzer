# Projektstruktur

Diese Datei ist als schneller Einstieg fuer spaetere Wartung gedacht.

## Ordner

### `functions/`

Gemeinsame Logik fuer:

- CSV lesen
- Zeit filtern
- Plotten
- Schwellwerte finden
- Konsolen-Ausgaben erzeugen

### `plotter/`

GUI-Anwendung fuer interaktive Auswahl von:

- Datei
- Record Type
- System
- X-Achse
- Y-Spalten

### `input/`

Beispiel- und Testdateien.

### `docs/`

Technische Dokumentation fuer Menschen, die das Projekt spaeter pflegen:

- `function_dependencies.md`: wer von wem abhaengt
- `project_structure.md`: schneller Einstieg in die Struktur

## Wichtigste Dateien

### `log_analyzer.py`

Erzeugt PNG-Plots aus der Kommandozeile.

### `peak_finder.py`

Findet Schwellwert-Ueber- und -Unterschreitungen.

### `plotter/csv_plotter.py`

Interaktive GUI fuer CSV-Dateien.

## Grundidee der Architektur

Die Kernlogik ist moeglichst in kleine Module zerlegt:

- Eingabe und Pfade
- Parsen
- Filtern
- Auswerten
- Darstellen
- Berichten

Der Vorteil ist, dass spaetere Aenderungen gezielter moeglich sind:

- neue CLI-Optionen aendern meist nur die Einstiegspunkte
- neue Plot-Darstellung aendert meist nur Plotter/Plotting
- neues CSV-Format betrifft meist zuerst Parser und Plotter-Metadaten
