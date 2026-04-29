# CLI-Ablaufe

Dieses Dokument beschreibt die wichtigsten Arbeitsablaeufe der beiden Terminal-Programme.

## Plot-Analyse

```mermaid
sequenceDiagram
  participant Nutzer
  participant CLI as log_analyzer.py
  participant Parser as csv_parser
  participant Filter as time_filters
  participant Plot as plotting
  participant Report as reporting

  Nutzer->>CLI: CSV-Datei und Parameter uebergeben
  CLI->>Parser: Datei lesen und Messreihen bauen
  Parser-->>CLI: ParsedSeries
  CLI->>Filter: optionales Zeitfenster anwenden
  Filter-->>CLI: gefilterte Daten
  CLI->>Plot: PNG erzeugen
  CLI->>Report: Kennzahlen ausgeben
```

## Schwellwertsuche

```mermaid
sequenceDiagram
  participant Nutzer
  participant CLI as peak_finder.py
  participant Parser as csv_parser
  participant Filter as time_filters
  participant Finder as thresholds
  participant Report as threshold_reporting

  Nutzer->>CLI: CSV-Datei und Grenzwerte uebergeben
  CLI->>Parser: Datei lesen und Messreihen bauen
  Parser-->>CLI: ParsedSeries
  CLI->>Filter: optionales Zeitfenster anwenden
  Filter-->>CLI: gefilterte Daten
  CLI->>Finder: Grenzuebergaenge berechnen
  Finder-->>CLI: Ereignisliste
  CLI->>Report: Ereignisse ausgeben
```

## Warum diese Trennung sinnvoll ist

- Parser, Filter und Auswertung koennen getrennt getestet und verstanden werden.
- Fehler in einem Schritt lassen sich schneller eingrenzen.
- Neue Ausgabekanaele koennen spaeter leichter ergaenzt werden.
