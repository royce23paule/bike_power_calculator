# Bike Power Calculator – Streamlit

## Version 1.6

Feinprofilierung des Rechenkerns:

- `bike_power_main_calc()` wird intern weiter aufgeteilt
- gemessen werden:
  - Steigung/Leistungsinput
  - `calc_v()` inkl. Wetter/CdA/Geschwindigkeitslösung
  - Leistungsanteile
  - Listen/Speichern
  - laufende NP/AP-Aktualisierung
- Die Berechnung selbst bleibt unverändert.
- Ziel: präzise sehen, wo der Hauptlauf Zeit verliert, bevor wir optimieren.

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```
