# Bike Power Calculator – Version 2.4

Version 2.4 optimiert die Berechnung langer FIT-Dateien, ohne die physikalischen Formeln zu verändern.

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
