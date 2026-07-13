# Changelog

## 2.6.1
- Behoben: `NameError` für `_kernel_profile`
- Profiler-Speicher liegt jetzt auf Modulebene und wird pro Lauf zurückgesetzt


## 2.6
- Detailliertes Profiling innerhalb von `bike_power_main_calc()`
- Zeit pro Abschnitt
- Aufrufszahlen und Millisekunden pro Aufruf
- Top-5-Zeitfresser im Entwicklermodus
- Keine Änderung der Berechnungslogik


## 2.4

### Performance
- AP/NP-Endwerte werden nach der Punktschleife einmalig berechnet.
- Vermeidet O(n²)-Summierung bei langen FIT-Dateien.

### Unverändert
- Physikalische Berechnung, Iterationsziele und Ausgabeformate.

## 2.3

### Neu
- Automatischer Benchmarkvergleich im Entwicklermodus
- Vergleich von Radzeit, Distanz, Geschwindigkeit, AP, NP und Höhenmetern
- Toleranzbasierter Status je Kennzahl
- Performancevergleich des Bike-Power-Hauptlaufs
- Anzeige der Wetter-Cache-Treffer, Fehlschläge und API-Anfragen

### Unverändert
- Physikalische Berechnung
- Online-Wettermodell
- PDF- und Kartenlogik
