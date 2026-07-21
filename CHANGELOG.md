# Changelog

## 3.9.4
- Sämtliche Rechner-Eingabefelder in ein gepuffertes Streamlit-Formular verschoben
- Zahlenwerte können nacheinander geändert werden, ohne nach jeder Eingabe die Seite neu zu laden
- Neuer Button „Einstellungen übernehmen“
- „Berechnung starten“ übernimmt alle geänderten Werte automatisch
- PDF-, HTML- und Wetteroptionen werden ebenfalls gemeinsam übernommen
- Datei-Uploads bleiben weiterhin unmittelbar wirksam
- Ergebnisdiagramme werden während der Eingabe nicht mehrfach neu aufgebaut
- Keine Änderung der Berechnungsphysik


## 3.9.3
- Suche nach Studienname, Studientyp und Parametern
- Sortierung nach Favoriten, Änderungsdatum, Erstellungsdatum, Name oder Studientyp
- Auf- und absteigende Sortierreihenfolge
- Favoriten direkt in der Studienbibliothek verwalten
- Studien duplizieren und direkt umbenennen
- Mehrfachauswahl zum gemeinsamen Löschen
- Mehrfachlöschen erfolgt zuverlässig in einem einzigen Git-Commit
- Bestehende Einzel-Löschung verwendet ebenfalls den robusten Git-Workflow
- Keine Änderung der Berechnungsphysik


## 3.9.2.5
- Geladene 2D-Studien werden vor den Eingaben für eine neue Studie angezeigt
- Die Anzeige gespeicherter Studien benötigt keine aktuell gesetzte GPX/FIT-Datei mehr
- GPX/FIT ist nur noch Voraussetzung für das Starten einer neuen Studie
- Gleiches robustes Verhalten für geladene 1D-Studien
- Keine Änderung der Berechnungsphysik


## 3.9.2.4
- Einheitlicher aktiver Studienzustand für neue, lokale und aus GitHub geladene Studien
- Geladene 1D-/2D-Studie bestimmt unmittelbar den angezeigten Studientyp
- Radio-Widget-State wird beim Laden kontrolliert neu initialisiert
- Speicher-, Export- und Ergebnisanzeige lesen dieselbe aktive Studie
- Verhindert Erfolgsmeldung ohne sichtbare Studienergebnisse
- Keine Änderung der Berechnungsphysik


## 3.9.2.3
- GitHub-Aktionen „Als neue Studie speichern“ und „Ausgewählte aktualisieren“ klar getrennt
- Nach dem ersten Speichern oder Laden können beliebig weitere Studien neu gespeichert werden
- Neue 1D- und 2D-Berechnungen lösen automatisch die Verknüpfung zur zuvor ausgewählten GitHub-Studie
- Lokaler JSON-Import wird als eigenständige Studie behandelt
- GitHub-Laden behält die Verknüpfung für gezielte Aktualisierungen
- Neue Funktion „Auswahl lösen“
- Keine Änderung der Berechnungsphysik


## 3.9.2.2
- Studien speichern jetzt exakt wie Berechnungen per Git-Clone, lokalem Schreiben, einem Commit und Push
- Studien-Datei und Studienindex werden atomar im selben Commit gespeichert
- Kein REST-Contents- oder Git-Data-Upload mehr für Studien
- „Einstellungen laden“ wechselt automatisch zum Rechner und setzt die Widgetwerte erst dort
- „Alles laden“ übernimmt Settings und Ergebnisse und öffnet anschließend den Rechner
- Behebt das Entfernen geladener Widgetwerte auf der Datenbankseite durch Streamlit
- Keine Änderung der Berechnungsphysik


## 3.9.2.1
- GitHub-Studien werden komprimiert gespeichert
- Große Studien verwenden automatisch die Git-Data-API statt des Contents-Einzelrequests
- Korrekte SHA-Verwendung direkt nach dem erstmaligen Anlegen des Studienindex
- Rückwärtskompatibles Laden unkomprimierter Studien aus Version 3.9.2
- Rechner-Widgets werden beim Laden gespeicherter Settings zuverlässig zurückgesetzt
- „Einstellungen laden“ und „Alles laden“ übernehmen die gespeicherten Eingaben wieder vollständig
- Keine Änderung der Berechnungsphysik


## 3.9.2
- GitHub-Studienbibliothek für 1D- und 2D-Parameterstudien
- Studien mit UUID speichern und laden
- Studien umbenennen, duplizieren, favorisieren und löschen
- Zentraler Index unter Database/Studies/index.json
- Lokaler JSON-Import und -Export bleibt erhalten
- Keine Änderung der Berechnungsphysik


## 3.9.1
- Vollständige 1D- und 2D-Parameterstudien als JSON speichern
- Gespeicherte Studien wieder laden und automatisch dem richtigen Studientyp zuordnen
- Export enthält Parameterbereiche, Referenzwerte, Konfigurationen, Ergebnisse und App-Version
- Robuste JSON-Konvertierung für NumPy-, Pandas- und Datumswerte
- Validierung inkompatibler oder beschädigter Studiendateien
- Keine Änderung der Berechnungsphysik


## 3.9.0
- Zweidimensionale Parameterstudien mit frei wählbarer X- und Y-Achse
- Unterstützte Parameter: CdA, Leistung, Fahrergewicht und Crr
- Fahrzeit-Heatmap mit Zeitwerten in jeder Zelle
- Geschwindigkeits-Heatmap
- Referenzkombination als Stern markiert
- KPI für schnellste Kombination, Zeitspanne und Anzahl der Simulationen
- Ergebnistabelle und CSV-Export
- Separate Sitzungsspeicherung für 1D- und 2D-Studien
- Begrenzung auf maximal 8 Werte je Achse und 36 Simulationen
- Keine Änderung der Berechnungsphysik


## 3.8.2
- Deutlich sichtbare Referenzmarkierung als Stern in den Studiendiagrammen
- Erweiterte Hover-Informationen mit Fahrzeit, Referenzdifferenz, Geschwindigkeit, AP und NP
- Sensitivitäts-KPI mit sinnvoller Einheit je Parameter
- Automatische Kernaussagen zu Linearität, Zeitspannweite und verändertem Grenznutzen
- Referenzpunkt wird in der Ergebnistabelle gekennzeichnet
- Keine Änderung der Berechnungsphysik


## 3.8.1
- Referenzorientierte Auswertung von Parameterstudien
- KPI-Karten für schnellste Variante, Referenzpunkt, Referenzdifferenz und Zeitspannweite
- Interaktive Diagramme für Fahrzeit, Zeitgewinn, Geschwindigkeit, AP und NP
- Automatisches Kurzfazit zur Wirkung des untersuchten Parameters
- Referenzpunkt wird als nächstgelegener Studienwert zum aktuellen Rechnerwert markiert
- Erweiterte Ergebnistabelle und CSV-Export
- Keine Änderung der Berechnungsphysik


## 3.8.0.1
- StreamlitInvalidNumberFormatError in der Parameterstudie behoben
- Zahlenfelder verwenden jetzt gültige Streamlit-Formatstrings
- Explizite minimale Schrittweiten für alle Studienparameter
- Keine Änderung der Berechnungsphysik


## 3.8.0
- Universelle Basis für eindimensionale Parameterstudien
- Neue Analyseart „Parameterstudie“
- Unterstützte Parameter: CdA flach, Leistung bei 0 %, Fahrergewicht und Crr
- Maximal 25 automatische Simulationen pro Studie
- Fortschrittsanzeige und aktueller Simulationswert
- Ergebnisse bleiben während der Browser-Sitzung erhalten
- Ergebnistabelle und CSV-Export
- Gemeinsamer Einstiegspunkt `run_single_simulation` für Rechner und Studien
- Studien verwenden exakt denselben Rechenkern wie normale Berechnungen
- PDF und HTML-Karte sind bei Studienläufen zur Laufzeitersparnis deaktiviert
- Keine Änderung der Berechnungsphysik


## 3.7.4.1
- NameError in der Vergleichskarte behoben
- Kartenfarbskala verwendet jetzt die vorhandene interne Farbfunktion
- Keine Änderung der Berechnungsphysik


## 3.7.4
- Gemeinsame Vergleichskarte für mehrere gespeicherte Berechnungen
- Sichtbarkeit einzelner Läufe direkt in der Analyse umschaltbar
- Feste Lauf-Farben für die eindeutige Zuordnung
- Gemeinsame Farbskala für Geschwindigkeit, Leistung, Wind, relative Luftgeschwindigkeit, Höhe und Steigung
- Frei einstellbare Linienbreite
- Automatische Kartenansicht abhängig von der Streckenausdehnung
- Tooltips mit Berechnungsname, Messwert und Distanz
- Bestehende Analyseauswahl und bereits geladene Ergebnisdaten werden wiederverwendet
- Keine Änderung der Berechnungsphysik


## 3.7.3
- Analysebereich als kompaktes Dashboard neu aufgebaut
- Berechnungsauswahl wird nur noch einmal gerendert und geladen
- KPI-Karten für Zeit, Geschwindigkeit, AP, NP, CdA und Höhenmeter
- Ein zentrales großes Plotly-Diagramm mit frei wählbarer Zeitreihe
- Differenztabelle gegenüber frei wählbarer Referenzberechnung
- Vollständige Vergleichstabelle in einklappbarem Bereich
- Gemeinsamer Analyse-Datensatz wird von allen Komponenten wiederverwendet
- Doppelte API-Aufrufe und doppelte Widgets im Analysebereich entfernt
- Keine Änderung der Berechnungsphysik


## 3.7.2
- Behebt StreamlitDuplicateElementKey im Analysebereich
- Jede Instanz der Vergleichs-Engine verwendet jetzt einen eigenen Key-Präfix
- Übersicht und Diagramme besitzen getrennte Widget- und Session-State-Schlüssel
- Auswahl, Cache, Kennzahl, Zeitreihe, Referenz und Plotly-Chart sind eindeutig
- Keine Änderung der Berechnungsphysik


## 3.7.1
- Neue Hauptnavigation mit Rechner, Analyse und Datenbank
- Vergleich aus der Datenbankverwaltung in den eigenständigen Analysebereich verschoben
- Analyse nutzt die volle Seitenbreite statt der schmalen Sidebar
- Datenbankbereich enthält nur noch Verwaltung: Events, Dateien, Berechnungen und Backup
- Analysebereich mit Tabs für Übersicht, Diagramme, Karte und Tabellen
- Vergleichs-Engine modularisiert und abschnittsweise wiederverwendbar
- Karten- und Tabellenvergleich für Version 3.7.2 vorbereitet
- Rechner und bestehende Ergebnisansicht bleiben unverändert nutzbar
- Keine Änderung der Berechnungsphysik


## 3.7.0
- Neuer Tab „Vergleich“ für gespeicherte Berechnungen eines Events
- Zwei bis acht vollständige Berechnungen gleichzeitig auswählbar
- Gemeinsame Kennzahlentabelle mit Zeit, Geschwindigkeit, AP, NP, CdA und Höhenmetern
- Vergleichstabelle als CSV exportierbar
- Balkenvergleich für Fahrzeit, Geschwindigkeit, AP, NP und CdA
- Gemeinsame interaktive Verlaufskurven über Strecke oder relative Strecke
- Vergleich von Geschwindigkeit, Leistung, Wind, Luftgeschwindigkeit, Höhe, Steigung, Luftdichte und CdA
- Differenztabelle gegenüber einer frei wählbaren Referenzberechnung
- Vergleichs-Engine als Grundlage für spätere Parameterstudien
- Keine Änderung der Berechnungsphysik


## 3.6.1
- Event-Löschung entfernt rekursiv das vollständige Eventverzeichnis
- Alle Berechnungen, PDF-, HTML-, Wetter-, Eingabe- und versteckten Dateien werden mitgelöscht
- index.json wird erst nach erfolgreicher vollständiger Löschung aktualisiert
- Verbesserter Löschdialog mit Eventname sowie Anzahl der Berechnungen und Dateien
- PDF-Vorschau startet standardmäßig mit Zoom 2,5
- Zoom-Bereich der PDF-Vorschau auf 1,0 bis 4,0 erweitert
- Repository-Statistik wird nach wichtigen Datenbankänderungen automatisch aktualisiert
- Keine Änderung der Berechnungsphysik


## 3.6.0
- Event-ZIP-Backups können als neues Event mit neuer UUID importiert werden
- ZIP-Struktur und Pfade werden vor dem Import validiert
- Gespeicherte Berechnungen können umbenannt werden
- Automatische Integritätsprüfung für jede Berechnung
- Beschädigte Berechnungen werden markiert und nicht geladen
- Repository-Statistik: Events, Berechnungen, Dateien, Speicher und größte Datei
- Git-Push mit automatischem Wiederholungsversuch
- Keine Änderung der Berechnungsphysik


## 3.5.0
- Vollständiges Dateimanagement im GitHub-Event
- Event-Dateien können geladen, heruntergeladen, umbenannt und bestätigt gelöscht werden
- JSON-Wetter-Snapshots werden automatisch als Wetterdatei erkannt
- Dateityp, Größe und SHA-256-Prüfsumme werden angezeigt
- event.json bleibt unsichtbar und gegen Löschen sowie Umbenennen geschützt
- Gesamtes Event kann einschließlich Berechnungen als ZIP-Backup exportiert werden
- Verbliebene automatische settings.json-Option beim Bearbeiten eines Events entfernt
- Keine Änderung der Berechnungsphysik


## 3.4.4
- Gespeicherte Berechnungen können im Tab „Berechnungen“ dauerhaft gelöscht werden
- Löschung umfasst calculation.json, result.json, settings_snapshot.json, profiler.json, Log, PDF und HTML
- Explizite Löschbestätigung erforderlich
- event.json wird in der Dateiansicht nicht mehr angezeigt
- event.json ist zusätzlich serverseitig vor dem Löschen geschützt
- Keine Änderung der Berechnungsphysik


## 3.4.3
- Offline-Wetter wird unabhängig vom ursprünglichen Fahrzeitverlauf räumlich rekonstruiert
- Exakte Treffer werden unverändert verwendet
- Sonst Interpolation aus den zwei nächstgelegenen Snapshot-Punkten desselben Tages
- Temperatur, Feuchte, Druck, Niederschlag, Windgeschwindigkeit und Böen linear interpoliert
- Windrichtung zirkulär über Vektorkomponenten interpoliert
- Räumlicher Sicherheitsradius auf 15 km erweitert; außerhalb weiterhin bewusster Abbruch
- Keine Änderung der übrigen Berechnungsphysik


## 3.4.2
- Offline-Wetter-Snapshots verwenden bei fehlendem exakten Schlüssel den nächstgelegenen Wetterpunkt desselben Tages
- Maximale räumliche Zuordnungstoleranz: 2,0 km
- Distanzberechnung mit Haversine-Formel
- Robust gegenüber leicht abweichenden GPX-Stützpunkten zwischen zwei Berechnungen
- Fehlermeldung nennt die Entfernung zum nächsten vorhandenen Snapshot-Punkt
- Keine Änderung der Berechnungsphysik außerhalb der Wetterpunkt-Zuordnung


## 3.4.1
- Behoben: `_weather_request_key` war versehentlich auskommentiert
- Online-Wetterberechnungen und Wetter-Snapshots funktionieren wieder
- Wetter-Schlüssel werden stabil aus Koordinaten und Datum erzeugt
- Keine Änderung der Berechnungsphysik


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
