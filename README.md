# Bike Power Calculator – Streamlit

## Version 1.5

Weitere Laufzeitoptimierung:

- PDF-Erzeugung ist jetzt optional
- HTML-Kartenerzeugung ist jetzt optional
- Beide Optionen sind in der Sidebar unter „Ausgabe“
- Standardmäßig bleiben PDF und HTML-Karte aktiviert
- Für schnelle Tests kann die PDF ausgeschaltet werden

## Erwarteter Effekt

Im Profil der Challenge-Roth-Standardberechnung dauerte das PDF-Schreiben ca. 8 Sekunden.
Wenn `PDF erzeugen` deaktiviert wird, entfällt dieser Block vollständig.

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```
