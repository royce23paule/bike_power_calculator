# Bike Power Calculator – Streamlit

## Version 1.0

Aufgeräumte Repository-Struktur:

```text
BikePowerCalculator/
├── app.py
├── bike_power_calc.py
├── defaults.py
├── open_meteostat.py
├── requirements.txt
├── README.md
└── data/
    ├── Default_INPUT.json
    └── Challange_Roth_Bike_2025.gpx
```

## Wichtig

Die Standardwerte liegen jetzt in:

```text
data/Default_INPUT.json
```

Die Standard-GPX liegt in:

```text
data/Challange_Roth_Bike_2025.gpx
```

Die App lädt beide automatisch. Ein Benutzer kann nach dem Start direkt auf **Berechnung starten** klicken.

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud

Bei GitHub alle Dateien und den kompletten `data`-Ordner hochladen.
Als Main file bleibt `app.py`.
