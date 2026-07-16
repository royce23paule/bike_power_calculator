# Changelog

## 3.4.0
- Vollständige Open-Meteo-Antworten werden als reproduzierbarer JSON-Wetter-Snapshot erfasst
- JSON-Wetter-Snapshots können über denselben Wetterdatei-Upload wie CSV geladen werden
- Dateiendung steuert automatisch das Wettermodell: CSV vereinfacht, JSON vollständige Online-Daten
- Geladene JSON-Snapshots arbeiten vollständig offline ohne erneuten API-Abruf
- Wetter-Snapshot steht nach jeder Online-Berechnung als Download bereit
- Wetter-Snapshot wird beim Speichern einer Berechnung automatisch separat archiviert
- Alles laden stellt auch die gespeicherte Wetterdatei wieder her
- Keine Änderung der Berechnungsphysik


## 3.3.1
- Laden gespeicherter Berechnungsdateien auf GitHub Raw-Media-Abruf umgestellt
- Behebt JSONDecodeError bei per Git-Commit/Push gespeicherten Dateien
- calculation.json, result.json, profiler.json und run_log.txt werden korrekt geladen
- Verständlichere Fehlermeldung bei tatsächlich ungültigem JSON
- Keine Änderung der Berechnungsphysik


## 3.3.0
- Gespeicherte Berechnungen im GitHub-Event auswählen und laden
- Aktionen: Ergebnisse laden, Einstellungen laden oder Alles laden
- Alles laden stellt Ergebnis, Profiler, Log, PDF und HTML-Karte wieder her
- Neue Events erzeugen keine automatische settings.json mehr
- Aktuelle Einstellungen können im Event unter frei wählbarem JSON-Dateinamen gespeichert werden
- Alter lokaler Datenbankbereich vollständig aus Oberfläche und Paket entfernt
- Keine Änderung der Berechnungsphysik


## 3.2.0
- Aktuelle Berechnung direkt in einem ausgewählten GitHub-Event speichern
- Eigene UUID und frei wählbarer Name pro Berechnung
- Speichert calculation.json, settings_snapshot.json, result.json, profiler.json und run_log.txt
- Vorhandene PDF und HTML-Karte optional mitspeichern
- Berechnungstyp wird automatisch erkannt
- Ergebnisse und Arrays werden JSON-kompatibel serialisiert
- Neue Events speichern immer automatisch die aktuellen vollständigen Einstellungen als settings.json
- Anzahl gespeicherter Berechnungen wird beim Event angezeigt
- Keine Änderung der Berechnungsphysik


## 3.1.7
- Behoben: fehlender `Path`-Import im Git-Commit/Push-Dateiweg
- Git-CLI-Abhängigkeiten statisch geprüft
- JSON-Upload bleibt unverändert
- Keine Änderung der Berechnungsphysik


## 3.1.6
- FIT/GPX-Upload vollständig von REST auf normalen Git-Commit/Push umgestellt
- Token wird über einen temporären HTTP-Authorization-Header an Git übergeben
- Token erscheint weder in Repository-URL noch in der Benutzeroberfläche
- Binärdateien werden unverändert als einzelne Repository-Datei gespeichert
- Laden größerer Dateien über GitHub Raw-Media-Type
- Legacy-Unterstützung für frühere mehrteilige Dateien bleibt erhalten
- Keine Änderung der Berechnungsphysik


## 3.1.5
- Teilgröße für FIT/GPX von 384 KB auf 48 KB reduziert
- Uploadstatus zeigt geschätzte Anzahl der Dateiteile
- Fehlermeldung nennt den konkret betroffenen Teil und dessen Größe
- Keine Änderung der Berechnungsphysik


## 3.1.4
- FIT/GPX werden in kleine Teile von 384 KB zerlegt
- Jeder Teil wird separat über die bewährte Contents-API gespeichert
- Manifest speichert Dateiname, Größe, Prüfsumme und Reihenfolge
- Dateien werden beim Laden transparent zusammengesetzt und geprüft
- Dateiliste zeigt mehrteilige Dateien als eine logische Datei
- Mehrteilige Dateien können vollständig gelöscht und dupliziert werden
- Keine Änderung der Berechnungsphysik


## 3.1.3
- Stufengenaue Diagnose für Git-Blob-Uploads
- Fehler unterscheiden Blob, Tree, Commit und Branch-Update
- Anzeige von HTTP-Status, Content-Type und GitHub Request-ID
- Token und Authorization-Header werden nicht ausgegeben
- Keine Änderung der Berechnungsphysik


## 3.1.2
- FIT- und GPX-Dateien verwenden immer die Git-Blob/Tree/Commit-API
- Dateigröße spielt für FIT/GPX keine Rolle mehr
- Uploadstatus zeigt den tatsächlich verwendeten Uploadweg
- Kleine JSON-/CSV-Dateien nutzen weiterhin die Contents-API
- Keine Änderung der Berechnungsphysik


## 3.1.1
- Robuster Upload größerer FIT-/GPX-Dateien über Git-Blobs, Trees und Commits
- Kleine JSON-/CSV-Dateien nutzen weiterhin die Contents-API
- Automatische Umschaltung ab 750 KB
- Uploadstatus zeigt Dateiname, Größe und Fortschritt
- Keine Änderung der Berechnungsphysik


## 3.1.0
- Vollständige GitHub-Eventverwaltung
- Doppelte Eventnamen werden erkannt und angezeigt
- Event-Metadaten bearbeiten und umbenennen
- Aktuelle settings.json eines Events aktualisieren
- Events inklusive Dateien duplizieren
- Events mit Sicherheitsabfrage löschen
- JSON-, GPX-, FIT- und CSV-Dateien hochladen
- Dateien herunterladen, in die App laden und löschen
- UUID bleibt bei Umbenennung stabil
- Keine Änderung der Berechnungsphysik


## 3.0.0
- GitHub-Datenbank-Grundlage
- GitHubDatabase-Klasse und Streamlit-Secrets
- Verbindungstest und index.json-Initialisierung
- Events mit UUID, event.json und vollständiger settings.json
- Events suchen und Einstellungen laden
- Lokale Datenbank bleibt als Fallback


## 2.13.2
- Behoben: fehlender `datetime`-Import in der Event-Datenbank
- Zeitstempel für Event-Metadaten funktionieren wieder
- Keine Änderung der Berechnungslogik


## 2.13.1
- Behoben: fehlender `re`-Import in der Event-Datenbank
- Event-IDs können wieder korrekt erzeugt werden
- Keine Änderung der Berechnungslogik


## 2.13
- Lokale Event-Datenbank eingeführt
- Events mit Datum, Ort, Typ, Tags und Notizen anlegen
- Events suchen und auswählen
- JSON-, GPX-, FIT- und CSV-Dateien einem Event zuordnen
- JSON-Einstellungen direkt aus der Datenbank laden
- GPX-/FIT-Dateien direkt in die Eingaben übernehmen
- Dateien anzeigen und löschen
- Grundstruktur für gespeicherte Berechnungen und Dokumente
- Keine Änderung der Berechnungsphysik


## 2.12.5
- Höhenreihe explizit als numerische Liste exportiert
- Höhe bleibt unabhängig von leichten Längenabweichungen auswählbar
- Tooltip nutzt sicheren Index für Höhenwerte
- Keine Änderung der Berechnungsphysik


## 2.12.4
- Höhe zuverlässig als auswählbare Kartengröße verfügbar
- Höhenwert im Tooltip korrigiert
- Alle Tooltip-Werte auf zwei Nachkommastellen formatiert
- Windgeschwindigkeit und Windrichtung entlang der Strecke aus den zeitabhängigen Wetterdaten übernommen
- Konstante Windanzeige bei Advanced Weather behoben
- Keine Änderung der Rechenphysik; Korrekturen betreffen Kartendaten und Darstellung


## 2.12.3
- Windrichtungspfeile standardmäßig aktiviert
- Pfeilrichtung an meteorologische Windrichtung angepasst
- Windbetrag und vorzeichenbehaftete Längskomponente getrennt
- Negative Werte nur noch bei „Windkomponente längs“
- Relative Luftgeschwindigkeit vektoriell aus Bike- und Windvektor berechnet
- Tooltip zeigt alle auswählbaren Größen plus Windrichtung
- Keine Änderung der Rechenphysik; Korrekturen betreffen die Kartendarstellung


## 2.12.2
- Windpfeile als robuste LineLayer-Kombination mit sichtbarer Pfeilspitze
- Pfeilschaft und zwei Pfeilkopfsegmente
- Ungültige Startwerte werden weiterhin übersprungen
- Farbskala unter der Karte ergänzt
- Farbskala zeigt 5.- bis 95.-Perzentil der gewählten Größe
- Keine Änderung der Berechnungsphysik


## 2.12.1
- Alte HTML-Karte standardmäßig deaktiviert
- Windlinien durch echte Richtungspfeile mit sichtbarer Spitze ersetzt
- Ungültige Start-/Endwerte werden übersprungen
- Pfeilgröße begrenzt und nur moderat von der Windgeschwindigkeit abhängig
- Keine Änderung der Berechnungsphysik


## 2.12
- Neue interaktive GPS-Trackkarte in der vollständigen Auswertung
- Einfärbung nach Geschwindigkeit, Leistung, Wind, relativer Luftgeschwindigkeit, Höhe oder Steigung
- Optionale Windrichtungspfeile mit einstellbarem Abstand
- Start-/Zielmarkierung und Tooltips
- Bestehender HTML-Kartenexport bleibt erhalten
- Keine Änderung der Berechnungsphysik


## 2.11.5
- Veraltete Versions- und Build-Angaben projektweit aktualisiert
- Zentrale Konstanten für App-Version, Build-Datum und Rechenkernversion
- Average Power und Normalized Power direkt unter den Ergebnis-Kennzahlen
- Keine Änderung der Berechnungslogik


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
