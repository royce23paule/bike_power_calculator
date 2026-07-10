# Entwicklung

## Architektur
- `app.py`: Einstiegspunkt
- `app_main.py`: Streamlit-Oberfläche und Adapter
- `bike_power_calc.py`: Rechenkern
- `defaults.py`: Felddefinitionen und Default-Konfiguration
- `data/`: Referenzdaten

## Regeln
1. Eine klar abgegrenzte Änderung pro Version.
2. UI und Rechenkern nicht gleichzeitig ändern.
3. Vor Performance-Optimierungen zuerst messen.
4. Referenzlauf mit `data/Default_INPUT.json` und der Challenge-Roth-GPX.
5. Alle Python-Dateien vor Release kompilieren.

## Version 2.1
Nur UI-/Diagnoseänderungen; Rechenkern unverändert.
