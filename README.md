# Bike Power Calculator – Version 2.1

## Neu
- Entwicklermodus in der Sidebar
- Systeminformationen und Diagnosewerte
- Laufzeitprofile nur bei aktiviertem Entwicklermodus
- In-App-Changelog und Projektinformationen

## Start
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Referenzdaten
- `data/Default_INPUT.json`
- `data/Challange_Roth_Bike_2025.gpx`


## Version 2.2 – Online-Wetter-Cache

- Open-Meteo-Antworten werden 30 Tage persistent zwischengespeichert.
- Identische Wiederholungsberechnungen benötigen keine erneuten Netzwerkabfragen.
- Mit **Online-Wetter neu laden** kann der Cache bewusst geleert werden.
- Der erste Lauf mit neuen Koordinaten bleibt netzwerkabhängig; Folgeläufe sollten deutlich schneller sein.
