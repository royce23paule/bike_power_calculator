# Bike Power Calculator – Streamlit

## Version 0.9

Änderungen gegenüber Version 0.8:

- Standard-GPX liegt jetzt sauber unter `data/Challange_Roth_Bike_2025.gpx`
- `Default_INPUT.json` verweist auf diesen relativen Repository-Pfad
- Die App löst relative Pfade automatisch auf
- Beim ersten Start ist die Challenge-Roth-Strecke direkt aktiv
- Ein Benutzer kann sofort auf „Berechnung starten“ klicken, ohne eine GPX-Datei hochzuladen

## Repository-Struktur

```text
BikePowerCalculator/
├── app.py
├── bike_power_calc.py
├── defaults.py
├── open_meteostat.py
├── requirements.txt
├── README.md
├── Default_INPUT.json
└── data/
    └── Challange_Roth_Bike_2025.gpx
```

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```
