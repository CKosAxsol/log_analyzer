# ADR-001: Projektstruktur mit schlanken Einstiegspunkten

## Status

Angenommen

## Kontext

Das Projekt bietet mehrere Startwege: zwei CLI-Programme und eine GUI. Ohne klare Trennung wuerde dieselbe Logik schnell mehrfach in grossen Startdateien landen.

## Entscheidung

- Einstiegspunkte in `main/` bleiben moeglichst schlank.
- Gemeinsame Fachlogik liegt im Ordner `functions/`.
- Dokumentation wird im Ordner `docs/` gesammelt.
- Arbeitsanweisungen und Abhaengigkeiten werden zusaetzlich im Ordner `manifest/` festgehalten.

## Folgen

Vorteile:

- Wiederverwendung gemeinsamer Logik wird einfacher.
- Aenderungen sind gezielter moeglich.
- Die Projektstruktur bleibt fuer spaetere Wartung leichter lesbar.

Nachteile:

- Es gibt mehr Dateien, die man beim ersten Einstieg ueberblicken muss.
- Bei kleinen Anpassungen muss man gelegentlich zwischen Einstiegspunkt und Hilfsmodul wechseln.
