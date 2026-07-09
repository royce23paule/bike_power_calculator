# Bike Power Calculator – Streamlit

## Version 1.1.1

Hotfix gegenüber Version 1.1:

- `plotly` wird in `requirements.txt` auf `plotly==5.24.1` gepinnt.
- Sonst unverändert zu Version 1.1.
- Gedacht als Fix für Installationsprobleme auf Streamlit Community Cloud.

## Falls Streamlit Cloud trotzdem meckert

In Streamlit Cloud unter **Manage app → Logs** die genaue Fehlermeldung ansehen.
Wichtig ist die Zeile direkt über `ERROR: Could not install packages...`.

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```
