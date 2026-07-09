# Bike Power Calculator – Streamlit

## Stand Version 0.4

Korrekturen gegenüber Version 0.3:

- JSON-Upload überschreibt jetzt auch die bereits vorhandenen Streamlit-Widget-Werte.
- Nach dem Laden einer JSON-Datei wird die App automatisch neu geladen.
- Fehlerprotokoll enthält jetzt den vollständigen Python-Traceback.
- Typische Null-Division-Stellen in Hilfsfunktionen wurden defensiv abgesichert.
- Fehlende GPX/FIT- oder Wetterdateien werden vor der Berechnung klar gemeldet.

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```
