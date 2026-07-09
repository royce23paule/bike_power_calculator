# Bike Power Calculator – Streamlit

## Version 1.4

Erste echte Laufzeitoptimierung:

- Wenn `max. Leistung (Liste( [W]` nur einen einzigen Wert enthält, wird der bisher redundante Optimierungslauf übersprungen.
- Der Hauptlauf bleibt unverändert und erzeugt weiterhin die finalen Ergebnisse.
- Bei mehreren Maximalleistungswerten bleibt das bisherige Such-/Optimierungsverhalten unverändert.
- Erwartete Beschleunigung beim aktuellen Challenge-Roth-Default: ca. 8 Sekunden weniger.

## Hintergrund

Im Profil aus Version 1.3 waren zwei vollständige Bike-Power-Läufe sichtbar:
- Optimierungslauf ca. 8.3 s
- Hauptlauf ca. 8.4 s

Bei nur einem Wert in der Leistungsliste gibt es nichts zu optimieren. Deshalb kann der erste Lauf ohne Ergebnisänderung entfallen.

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```
