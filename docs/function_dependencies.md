# Funktions-Abhaengigkeiten

Dieses Dokument beschreibt, welche Dateien und Funktionen im Projekt
voneinander abhaengen und welche Aufgabe sie im Gesamtablauf haben.

## 1. Gesamtueberblick

Es gibt drei Einstiegspunkte:

- `main/log_analyzer.py`
- `main/peak_finder.py`
- `main/csv_plotter.py`

Die ersten beiden sind Terminal-Programme. Der Plotter ist eine kleine GUI.

## 2. Abhaengigkeiten der Terminal-Tools

### `main/log_analyzer.py`

Verantwortung:

- Kommandozeilenparameter einlesen
- CSV-Datei(en) finden
- Daten parsen
- optional nach Zeit filtern
- PNG erzeugen
- kurze Konsolen-Zusammenfassung ausgeben

Abhaengigkeiten:

```text
main/log_analyzer.py
 -> functions.cli.parse_args
 -> functions.path_utils.resolve_csv_path
 -> functions.dependencies.ensure_dependencies
 -> functions.csv_parser.parse_csv
 -> functions.time_filters.parse_optional_timestamp
 -> functions.time_filters.filter_series_by_time
 -> functions.plotting.plot_series
 -> functions.reporting.print_summary
```

### `main/peak_finder.py`

Verantwortung:

- Kommandozeilenparameter einlesen
- CSV-Datei(en) finden
- Daten parsen
- optional nach Zeit filtern
- Schwellwert-Uebergaenge finden
- Ereignisse in der Konsole ausgeben

Abhaengigkeiten:

```text
main/peak_finder.py
 -> parse_args
 -> validate_threshold_args
 -> functions.path_utils.resolve_csv_path
 -> functions.csv_parser.parse_csv
 -> functions.time_filters.parse_optional_timestamp
 -> functions.time_filters.filter_series_by_time
 -> functions.thresholds.find_threshold_events
 -> functions.threshold_reporting.print_threshold_summary
```

## 3. Abhaengigkeiten der GUI

### `main/csv_plotter.py`

Verantwortung:

- Datei auswaehlen
- CSV-Struktur erkennen
- moegliche X-Achsen und Y-Spalten sammeln
- Daten fuer den Plot einlesen
- Plot interaktiv anzeigen

Abhaengigkeiten:

```text
main/csv_plotter.py
 -> functions.dependencies.ensure_dependencies
 -> functions.csv_parser.open_csv_with_fallbacks
 -> functions.csv_parser.TIMESTAMP_COLUMN
 -> tkinter
 -> matplotlib
```

Wichtig:

- Der Plotter benutzt bewusst **nicht** direkt `functions.csv_parser.parse_csv`
  fuer alle Faelle.
- Grund: In der GUI kann die X-Achse frei gewaehlt werden.
- `parse_csv` aus `functions/csv_parser.py` ist dagegen fuer den CLI-Fall
  optimiert und erwartet immer `TimeStamp` als X-Achse.

## 4. Kernmodule im Ordner `functions`

### `functions/models.py`

Enthaelt die gemeinsamen Datenmodelle:

- `ParsedSeries`
- `ThresholdEvent`

Davon abhaengig:

```text
functions.models
 -> verwendet von csv_parser, plotting, reporting, time_filters, thresholds,
    threshold_reporting
```

### `functions/csv_parser.py`

Verantwortung:

- CSV-Datei mit geeigneter Textkodierung oeffnen
- APS/APU-Datenblock aus der Datei lesen
- Zeitstempel und numerische Werte in `ParsedSeries` umwandeln

Abhaengigkeiten:

```text
functions.csv_parser
 -> functions.models.ParsedSeries
```

### `functions/time_filters.py`

Verantwortung:

- Zeitargumente aus der CLI in `datetime` umwandeln
- vorhandene `ParsedSeries` auf einen Zeitbereich einschränken

Abhaengigkeiten:

```text
functions.time_filters
 -> functions.models.ParsedSeries
```

### `functions/plotting.py`

Verantwortung:

- aus einer `ParsedSeries` ein PNG erzeugen

Abhaengigkeiten:

```text
functions.plotting
 -> functions.models.ParsedSeries
 -> matplotlib
```

### `functions/reporting.py`

Verantwortung:

- kompakte Konsolen-Ausgabe fuer den normalen Plot-Lauf

Abhaengigkeiten:

```text
functions.reporting
 -> functions.models.ParsedSeries
```

### `functions/thresholds.py`

Verantwortung:

- Schwellwert-Ereignisse aus einer `ParsedSeries` berechnen

Abhaengigkeiten:

```text
functions.thresholds
 -> functions.models.ParsedSeries
 -> functions.models.ThresholdEvent
```

### `functions/threshold_reporting.py`

Verantwortung:

- Schwellwert-Ereignisse in lesbarer Form ausgeben

Abhaengigkeiten:

```text
functions.threshold_reporting
 -> functions.models.ThresholdEvent
```

### `functions/dependencies.py`

Verantwortung:

- fehlende Python-Pakete bei Bedarf nachinstallieren

Aktuell genutzt von:

```text
functions.dependencies
 -> verwendet von log_analyzer.py
 -> verwendet von csv_plotter.py
```

### `functions/path_utils.py`

Verantwortung:

- Dateiargumente in absolute lokale Pfade umwandeln

Aktuell genutzt von:

```text
functions.path_utils
 -> verwendet von log_analyzer.py
 -> verwendet von peak_finder.py
```

### `functions/cli.py`

Verantwortung:

- CLI-Argumente fuer `main/log_analyzer.py` definieren

Aktuell genutzt von:

```text
functions.cli
 -> verwendet von log_analyzer.py
```

## 5. Datenfluss

### Normaler Plot-Lauf im Terminal

```text
CSV-Datei
 -> csv_parser.parse_csv
 -> models.ParsedSeries
 -> time_filters.filter_series_by_time
 -> plotting.plot_series
 -> reporting.print_summary
```

### Threshold-Lauf im Terminal

```text
CSV-Datei
 -> csv_parser.parse_csv
 -> models.ParsedSeries
 -> time_filters.filter_series_by_time
 -> thresholds.find_threshold_events
 -> threshold_reporting.print_threshold_summary
```

### Plot-Lauf in der GUI

```text
CSV-Datei
 -> csv_plotter._load_metadata
 -> csv_plotter._parse_structured_csv oder _parse_plain_csv
 -> csv_plotter._convert_x_values
 -> matplotlib-Plot im Fenster
```

## 6. Wartungshinweise

- Wenn sich das APS/APU-Dateiformat aendert, zuerst `functions/csv_parser.py`
  und die strukturierten Leser im Plotter pruefen.
- Wenn sich nur das Plot-Verhalten aendert, moeglichst `functions/plotting.py`
  oder `main/csv_plotter.py` aendern, nicht den Parser.
- Wenn neue gemeinsame Daten gebraucht werden, zuerst pruefen, ob sie in
  `ParsedSeries` oder in einem neuen Dataclass-Modell sauberer aufgehoben sind.
