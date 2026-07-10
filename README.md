# Bike Power Calculator – Streamlit

## Version 1.7

Strukturelles Refactoring ohne Änderung der Berechnung.

Neue Dateistruktur:

```text
BikePowerCalculator/
├── app.py
├── ui.py
├── calc_adapter.py
├── plots.py
├── profiling.py
├── exports.py
├── bike_power_calc.py
├── defaults.py
├── open_meteostat.py
├── requirements.txt
├── README.md
└── data/
    ├── Default_INPUT.json
    └── Challange_Roth_Bike_2025.gpx
```

Ziel:

- `app.py` ist deutlich schlanker
- UI, Plotly-Diagramme, Profiler und Downloads liegen in eigenen Modulen
- Berechnung bleibt unverändert
- weitere Optimierungen am Rechenkern werden dadurch sicherer und leichter

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```
