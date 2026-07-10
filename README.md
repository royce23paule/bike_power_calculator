# Bike Power Calculator – Version 2.0

Diese stabile Refactoring-Version basiert vollständig auf der funktionierenden Version 1.5.1.

## Struktur

```text
BikePowerCalculator/
├── app.py          # schlanker Streamlit-Einstieg
├── app_main.py     # bestehende, stabile Streamlit-Oberfläche
├── bike_power_calc.py
├── defaults.py
├── open_meteostat.py
├── requirements.txt
├── README.md
└── data/
    ├── Default_INPUT.json
    └── Challange_Roth_Bike_2025.gpx
```

## Sicherheit

- `bike_power_calc.py` wurde aus Version 1.5.1 unverändert übernommen.
- Die Streamlit-Logik wurde nicht funktional verändert.
- Alle Python-Dateien wurden vor dem Verpacken mit `py_compile` geprüft.

## Start

```bash
pip install -r requirements.txt
streamlit run app.py
```
