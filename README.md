# Bike Power Calculator – Streamlit

Streamlit-Migration der bestehenden lokalen Bike-Power-Calculator-App.

## Stand Version 0.3

Diese Version enthält:

- vollständige Streamlit-Oberfläche mit allen Parametern der bisherigen Tkinter-App
- Tabs für Fahrer/Rad, Aerodynamik, Leistung, Wetter, Strecke und Ausgabe
- Upload für GPX/FIT
- Upload für Wetter-CSV
- JSON-Einstellungen laden und speichern
- Anbindung an die bestehende Berechnungslogik
- PDF-Download nach der Berechnung
- HTML-Karten-Download und Kartenanzeige in Streamlit
- Cloud-sichere Anpassung von `os.startfile()` und `webbrowser.open()`

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud

Repository bei GitHub hochladen und als Main file `app.py` auswählen.
