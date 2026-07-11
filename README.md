# Bike Power Calculator – Version 2.3.1

Version 2.3.1 ergänzt im Entwicklermodus einen automatischen Vergleich des aktuellen Laufs mit `data/Benchmark_Reference_API.json`.

Verglichen werden:
- Radzeit
- Distanz
- mittlere Geschwindigkeit
- Average Power
- Normalized Power
- Höhenmeter
- Laufzeit des Bike-Power-Hauptlaufs
- Wetter-Cache-Statistik

Start:
```bash
streamlit run app.py
```


## Version 2.3.1

Behoben:
- `ZeroDivisionError` im Substratverlauf bei Streckenabschnitten mit 0 W.
- Der Fehler konnte insbesondere nach positiver Vorgabe des Höhengewinns auftreten.
- Bei 0 W werden Fett- und Kohlenhydratanteil für die Darstellung auf 0 gesetzt.
- Berechnungen bei positiven Leistungswerten bleiben unverändert.
