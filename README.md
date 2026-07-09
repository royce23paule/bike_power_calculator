# Bike Power Calculator – Streamlit

Streamlit-Migration der bestehenden lokalen Bike-Power-Calculator-App.

## Stand

Version 0.2 enthält:

- vollständige Streamlit-Oberfläche mit allen Parametern der bisherigen Tkinter-App
- Tabs für Fahrer/Rad, Aerodynamik, Leistung, Wetter, Strecke und Ausgabe
- Tooltips aus der bestehenden Desktop-App
- Upload für GPX/FIT
- Upload für Wetter-CSV
- JSON-Einstellungen laden
- JSON-Einstellungen herunterladen
- unveränderte Reihenfolge aller Parameter für die spätere Übergabe an die bestehende Berechnungslogik

Die eigentliche Berechnung wird in Version 0.3 angebunden.

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud

Repository bei GitHub hochladen und als Main file `app.py` auswählen.
