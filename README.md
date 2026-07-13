# Bike Power Calculator – Version 2.5

Version 2.5 optimiert die Berechnung langer FIT-Dateien, ohne die physikalischen Formeln zu verändern.

## Neu / verbessert

- Average Power und Normalized Power werden im Rechenkern nur noch einmal am Ende eines vollständigen Laufs berechnet.
- Die bisherige quadratische Laufzeit durch wiederholte Summen über alle vorherigen Punkte entfällt.
- Besonders FIT-basierte CdA-Kalibrierungen mit vielen Datenpunkten sollten dadurch stark beschleunigt werden.
- PDF, Karte, Wetterlogik und CdA-/NP-/AP-Iteration bleiben unverändert.

## Referenztest

Bitte beim FIT-Test insbesondere vergleichen:

- ermittelter CdA
- Zielgeschwindigkeit 32,4 km/h
- Average Power 171 W
- Normalized Power 184 W
- Fahrzeit / Durchschnittsgeschwindigkeit
- Höhenmeter
- Profilerzeit `Bike-Power-Kalkulation Hauptlauf`



Behoben:
- `ZeroDivisionError` im Substratverlauf bei Streckenabschnitten mit 0 W.
- Der Fehler konnte insbesondere nach positiver Vorgabe des Höhengewinns auftreten.
- Bei 0 W werden Fett- und Kohlenhydratanteil für die Darstellung auf 0 gesetzt.
- Berechnungen bei positiven Leistungswerten bleiben unverändert.


## Version 2.5

- Adaptive NP/AP-Kalibrierung für FIT-Dateien.
- Der Glättungswert springt anhand eines kalibrierten AP/NP-Surrogats direkt zum wahrscheinlich passenden Wert.
- Robuste alte Schrittlogik bleibt als Fallback erhalten.
- Maximal 12 NP/AP-Vollberechnungen verhindern Endlosschleifen.
- CdA-Suche und physikalischer Rechenkern bleiben unverändert.


## Version 2.6.1

Diese Version enthält ausschließlich detailliertes Rechenkern-Profiling.
Im Entwicklermodus werden Zeit, Aufrufszahl und mittlere Dauer pro Aufruf angezeigt.


## Version 2.8
Deep Profiler mit kumulierten Hauptläufen, calc_v-Aufschlüsselung und CSV-Export.


## Version 2.8

Beschleunigt die Online-Wetter-/Luftdichteauswertung durch einmalig vorbereitete numerische Arrays und direkte Interpolation. Die simulierte Zeit pro Streckenpunkt bleibt Grundlage der Wetterwerte; es wird keine feste Luftdichte pro Streckenpunkt angenommen.
