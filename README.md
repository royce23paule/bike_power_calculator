# Bike Power Calculator – Streamlit

## Version 1.1.2

Hotfix für interaktive Diagramme:

- Leistung nutzt jetzt den korrekten internen Verlauf `power`
- CdA nutzt jetzt `cdA_List`
- Luftdichte wird neu als `rho_List` gespeichert und geplottet
- Effektiver Wind wird neu als `v_w_List` gespeichert und geplottet
- Geschwindigkeitsverlauf wird nicht mehr fälschlich erneut mit 3.6 multipliziert
- Rohdaten-Tabelle enthält jetzt die korrekten Spaltennamen

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```
