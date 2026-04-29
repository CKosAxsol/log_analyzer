# Architektur

Dieses Dokument beschreibt den groben Systemaufbau und den Datenfluss des Projekts.

## Zielbild

Das Projekt besteht aus drei Einstiegspunkten:

- `main/log_analyzer.py` fuer Plot-Ausgabe als PNG im Terminal
- `main/peak_finder.py` fuer Schwellwertsuche im Terminal
- `main/csv_plotter.py` fuer eine interaktive Desktop-Oberflaeche

Die eigentliche Fachlogik liegt moeglichst gesammelt im Ordner `functions/`.
Dadurch bleiben die Einstiegspunkte schlank und die Wiederverwendung wird einfacher.

## Modulaufbau

```mermaid
flowchart TD
  A[CLI oder GUI] --> B[CSV einlesen]
  B --> C[Datenmodell ParsedSeries]
  C --> D[Zeitfilter]
  D --> E[Auswertung oder Plot]
  E --> F[Konsole, PNG oder GUI-Fenster]
```

## Verantwortlichkeiten

- `main/`: startet Programme und verbindet die einzelnen Verarbeitungsschritte
- `functions/csv_parser.py`: liest CSV-Dateien und baut daraus nutzbare Messreihen
- `functions/time_filters.py`: schraenkt Daten auf ein gewuenschtes Zeitfenster ein
- `functions/plotting.py`: erstellt PNG-Diagramme fuer die CLI-Nutzung
- `functions/thresholds.py`: erkennt Schwellwert-Uebergaenge
- `functions/reporting.py` und `functions/threshold_reporting.py`: erzeugen lesbare Konsolenausgaben
- `main/csv_plotter.py` plus `functions/csv_plotter_*`: stellen die interaktive GUI bereit

## Datenfluss

### CLI fuer Plot-Analyse

```mermaid
flowchart LR
  A[CSV-Datei] --> B[parse_csv]
  B --> C[filter_series_by_time]
  C --> D[plot_series]
  C --> E[print_summary]
```

### CLI fuer Schwellwertsuche

```mermaid
flowchart LR
  A[CSV-Datei] --> B[parse_csv]
  B --> C[filter_series_by_time]
  C --> D[find_threshold_events]
  D --> E[print_threshold_summary]
```

### GUI fuer interaktives Plotten

```mermaid
flowchart LR
  A[CSV-Datei] --> B[Metadaten erkennen]
  B --> C[Spalten und X-Achse waehlen]
  C --> D[Datenreihen laden]
  D --> E[Matplotlib im Fenster]
```

## Strukturprinzip

- Gemeinsame Logik gehoert nach `functions/`, nicht mehrfach in einzelne Startdateien.
- Einstiegspunkte sollen moeglichst nur steuern, nicht selbst Fachlogik enthalten.
- Wenn einzelne Dateien zu gross werden, sollen neue Hilfsfunktionen in passende Module ausgelagert werden.
