# Bike Power Calculator – Streamlit

## Stand Version 0.7.1

Hotfix gegenüber Version 0.7:

- `app.py` ist jetzt robust, falls auf Streamlit Cloud noch eine ältere `defaults.py` liegt.
- Der Import von `fields_for_group` wurde entfernt und als Fallback direkt in `app.py` integriert.
- Kompakte Eingabeansicht und Expertenmodus bleiben erhalten.

## Wichtig beim Upload

Bitte im GitHub-Repository wirklich alle Dateien aus dem ZIP ersetzen, besonders:

- `app.py`
- `defaults.py`
- `requirements.txt`

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```
