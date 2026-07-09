# Bike Power Calculator – Streamlit

## Version 1.3

Profiler-Verfeinerung:

- Der bisher große Block „Berechnung / PDF / Karte erzeugen“ wird jetzt intern aufgeteilt.
- Detailzeiten für GPX/FIT-Einlesen, Höhenprofil, Bike-Power-Kalkulation, Karten, Statistiken, Diagramme und PDF.
- Die Berechnung bleibt unverändert.
- Ziel: den echten Zeitfresser identifizieren, bevor optimiert wird.

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```
