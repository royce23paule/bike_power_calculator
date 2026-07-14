# Changelog

## 2.11.4
- Hauptbereich nutzt zuverlässig die vollständige verfügbare Breite
- Streamlit-Maximalbreite per CSS aufgehoben
- Diagramme, Tabellen und Expander dürfen volle Containerbreite verwenden
- Responsive Seitenabstände für kleinere Bildschirme
- Keine Änderung der Berechnungslogik


## 2.11.3
- Berechnungslog erfasst jetzt stdout und stderr
- Log wird zusätzlich im Ergebnisobjekt gespeichert
- Anzeige verwendet Session-Log mit Ergebnis-Fallback
- CdA-Kalibrierung nur bei FIT-Datei und positivem Speed_Soll
- Keine Änderung der Berechnungslogik


## 2.11.2
- Separater Bereich „Interaktive Diagramme“ entfernt
- Interaktive Rohdatenansicht entfernt
- Vollständige Auswertung als ein ausklappbarer Gesamtbereich
- Diagramme und Tabellen innerhalb direkt sichtbar
- Berechnungslog ausklappbar
- PDF standardmäßig deaktiviert
- Renderer-Funktionen vollständig erhalten


## 2.11
- Vollständige interaktive Auswertung aller PDF-Diagramme und PDF-Tabellen
- Vorhandene Matplotlib-Reportdaten werden ohne erneute Physikberechnung übernommen
- Gesamtbereich standardmäßig zugeklappt
- Einzelne Diagramme und Tabellen separat ausklappbar
- PDF bleibt als Dokumentation unverändert verfügbar


## 2.10.2
- fNP wird zuverlässig in der CdA-Kalibrierung angezeigt
- CdA-Startwert zusätzlich im Ergebnisbereich
- Keine Änderung der Berechnungslogik


## 2.10.1
- Durchschnittsgeschwindigkeit in der CdA-Kalibrierung korrekt angezeigt
- Hauptlaufanzahl aus dem Deep-Profiler übernommen
- Keine Änderung der Berechnungslogik


## 2.10
- Direkte CdA-Kalibrierungsübersicht in der App
- Anzeige von CdA, AP, NP, Geschwindigkeit, fNP, Moving-Average-Wert und Laufanzahl
- Soll/Ist-Vergleich mit Toleranzstatus
- FIT-Kalibrierung ohne PDF vollständig auswertbar
- Keine Änderung der Berechnungsphysik


## 2.9.1
- FIT-Cache-Debugausgabe ergänzt
- Anzeige von Hash, Pfad, Existenz, Lese-, Schreib- und Parsingzeit
- Entwickleransicht für FIT-Cache-Diagnose
- Keine Änderung der Berechnungslogik


## 2.9
- Inhaltsbasierter FIT-Parsing-Cache
- Cache berücksichtigt FIT-Datei sowie Start-/Enddistanz
- Wiederholungsberechnungen laden vorbereitete Arrays direkt aus `.npz`
- Cache-Treffer wird im Log und Entwicklerprofil angezeigt
- Keine Änderung der Rechenphysik


## 2.8
- Online-Wetterinterpolation auf vorbereitete NumPy-Arrays umgestellt
- Direkte O(1)-Indexberechnung statt wiederholter Datetime-Suche
- Exakter, ergebnisneutraler Cache für identische Simulationszeitpunkte
- Keine Änderung an Wettermodell oder physikalischen Formeln


## 2.8
- Kumuliertes Profil über alle FIT-Hauptläufe
- Konvergenztabelle mit NP, AP, Geschwindigkeit, CdA, Glättung und fNP
- Deep Profiling von calc_v()
- Statistik der analytischen kubischen Lösungszweige
- CSV-Export der Profilergebnisse
- Keine Änderung der Berechnungslogik


## 2.6.1
- Behoben: `NameError` für `_kernel_profile`
- Profiler-Speicher liegt jetzt auf Modulebene und wird pro Lauf zurückgesetzt


## 2.6
- Detailliertes Profiling innerhalb von `bike_power_main_calc()`
- Zeit pro Abschnitt
- Aufrufszahlen und Millisekunden pro Aufruf
- Top-5-Zeitfresser im Entwicklermodus
- Keine Änderung der Berechnungslogik


## 2.4

### Performance
- AP/NP-Endwerte werden nach der Punktschleife einmalig berechnet.
- Vermeidet O(n²)-Summierung bei langen FIT-Dateien.

### Unverändert
- Physikalische Berechnung, Iterationsziele und Ausgabeformate.

## 2.3

### Neu
- Automatischer Benchmarkvergleich im Entwicklermodus
- Vergleich von Radzeit, Distanz, Geschwindigkeit, AP, NP und Höhenmetern
- Toleranzbasierter Status je Kennzahl
- Performancevergleich des Bike-Power-Hauptlaufs
- Anzeige der Wetter-Cache-Treffer, Fehlschläge und API-Anfragen

### Unverändert
- Physikalische Berechnung
- Online-Wettermodell
- PDF- und Kartenlogik
