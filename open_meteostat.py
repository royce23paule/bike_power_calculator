"""
Zentrale Felddefinitionen für die Streamlit-Version des Bike Power Calculators.

Diese Datei wurde aus der bisherigen Tkinter-App abgeleitet.
Die Reihenfolge der Felder entspricht weiterhin exakt der alten data_name-Liste,
damit die spätere Übergabe an die bestehende Berechnungslogik unverändert möglich bleibt.
"""

from __future__ import annotations

from typing import Any


FIELDS: list[dict[str, Any]] = [{'key': 'field_00', 'index': 0, 'name': 'Titel', 'default': 'Default', 'help': '', 'type': 'text', 'group': 'basis', 'is_path': False}, {'key': 'field_01', 'index': 1, 'name': 'FTP [W]', 'default': 244, 'help': 'FTP in W', 'type': 'float', 'group': 'basis', 'is_path': False}, {'key': 'field_02', 'index': 2, 'name': 'Gewicht Fahrer [kg]', 'default': 74, 'help': 'Fahrergewicht in kg', 'type': 'float', 'group': 'basis', 'is_path': False}, {'key': 'field_03', 'index': 3, 'name': 'Gewicht Bike [kg]', 'default': 10, 'help': 'Radgewicht in kg (+Getränke,etc.)', 'type': 'float', 'group': 'basis', 'is_path': False}, {'key': 'field_04', 'index': 4, 'name': 'Rollwiderstand cr [-]', 'default': 0.003, 'help': 'Rollreibung der Reifen --> 0.003 passt für die GP 5000 recht gut', 'type': 'float', 'group': 'basis', 'is_path': False}, {'key': 'field_05', 'index': 5, 'name': 'cdA im Flachen [m^2]', 'default': 0.265, 'help': 'Luftwiderstand für Position im Flachen; bei Fit-Datei Nutzung kann cdA entsprechend vorgegebener Geschw. angepasst werden; dazu Soll-Geschw. [km/h] mit Komma hinter cdA Wert', 'type': 'text', 'group': 'aero', 'is_path': False}, {'key': 'field_06', 'index': 6, 'name': 'cdA am Berg [m^2]', 'default': 0.33, 'help': 'Luftwiderstand in Kletterhaltung', 'type': 'float', 'group': 'aero', 'is_path': False}, {'key': 'field_07', 'index': 7, 'name': 'Mechanischer Wirkungsgrad Bike [%]', 'default': 97, 'help': 'Wirkungsgrad des Gesamtrades in % --> 97% passt gut', 'type': 'float', 'group': 'basis', 'is_path': False}, {'key': 'field_08', 'index': 8, 'name': 'Steigung cdA Berg [%]', 'default': 3, 'help': 'Steigung in % ab der man von Unterlenkerhaltung (cdA_Flat) in Kletterhaltung (cdA_Hill) wechselt', 'type': 'float', 'group': 'aero', 'is_path': False}, {'key': 'field_09', 'index': 9, 'name': 'Steigung im Windschatten [%]', 'default': -3, 'help': 'Steigung in % ab der man im Windschatten fährt, bei noch steileren Passagen wird davon ausgegangen, dass kein Windschatten da ist', 'type': 'float', 'group': 'aero', 'is_path': False}, {'key': 'field_10', 'index': 10, 'name': 'Windschattenersparniss [%]', 'default': 0, 'help': 'Reduzierung/ Einsparung in % der Leistung, die man gegen den Luftwiderstand aufbringt (also Reduzierung von cdA) --> 40% war bei Rund um Köln gut passend', 'type': 'float', 'group': 'aero', 'is_path': False}, {'key': 'field_11', 'index': 11, 'name': 'Normalized Power Sollwert [W]', 'default': 207, 'help': 'Vorgabe Normalized Power in W, wonach pol_a0 ODER Fit-Input angepasst wird; bei einem Negativen Wert wird NP nicht angepasst', 'type': 'float', 'group': 'leistung', 'is_path': False}, {'key': 'field_12', 'index': 12, 'name': 'Leistung bei 0% Steigung [W]', 'default': 200, 'help': 'Bei gpx_File: Polynomkoeffizient für die Leistungsvorgabe abhängig der Steigung; entspricht der Leistung bei 0% Steigung   ODER   bei FIT-File: Durchschnittsleistung auf die der Fit-Input angepasst wird', 'type': 'float', 'group': 'leistung', 'is_path': False}, {'key': 'field_13', 'index': 13, 'name': 'max. Steigung Leistungserhoehung [%]', 'default': 9, 'help': 'Bis zu dieser maximalen Steigung in % wird die Leistung linear geteigert', 'type': 'float', 'group': 'leistung', 'is_path': False}, {'key': 'field_14', 'index': 14, 'name': 'min. Steigung Leistungssenkung [%]', 'default': -8, 'help': 'Bis zu dieser minimalen Steigung in % wird die Leistung linear reduziert', 'type': 'float', 'group': 'leistung', 'is_path': False}, {'key': 'field_15', 'index': 15, 'name': 'min. Leisung [W]', 'default': 0, 'help': 'Minimale Leistung in W auf die reduziert wird', 'type': 'float', 'group': 'leistung', 'is_path': False}, {'key': 'field_16', 'index': 16, 'name': 'max. Leistung (Liste( [W]', 'default': '[260,270]', 'help': 'Maximale Leistung in W auf die reduziert wird; Muss Liste sin, kann aber beliebig lang sein --> wird zur Suche der maximalen Geschwindigkeit verwendet', 'type': 'text', 'group': 'leistung', 'is_path': False}, {'key': 'field_17', 'index': 17, 'name': 'Lufttemperatur (Standardwetter) [°C]', 'default': 20, 'help': 'Lufttemperatur in °C', 'type': 'float', 'group': 'wetter', 'is_path': False}, {'key': 'field_18', 'index': 18, 'name': 'Windgeschwindigkeit (Standardwetter) [km/h]', 'default': 0, 'help': 'Windgeschwindigkeit in km/h', 'type': 'float', 'group': 'wetter', 'is_path': False}, {'key': 'field_19', 'index': 19, 'name': 'Windrichtung (Standardwetter) [deg]', 'default': 165, 'help': 'Windrichtung in [deg]; 0° bedeuted Wind von S nach N', 'type': 'float', 'group': 'wetter', 'is_path': False}, {'key': 'field_20', 'index': 20, 'name': 'Abschwaechung/ Abschattung Windgescheind [-]', 'default': 0.5, 'help': 'Windeinfluss verringern; zu BestBikeSplit passt: Open Cost = 1 (nur wenn Wind direkt vom Meer ohne Hindernisse), Dessert/Plains = 0.75, Mixed/Populated (passt zu mesiten Bedingungen, Default) = 0.5, Forrest/Mountain = 0.4, Inner City = 0.38', 'type': 'float', 'group': 'wetter', 'is_path': False}, {'key': 'field_21', 'index': 21, 'name': 'Verwendung Advanced Weather', 'default': 'True', 'help': 'Verwendung des Advanced Wettermodells; wenn True, danach mit , angeben ob Wetter aus online-API (Ture) oder CSV (False), Bei True noch Rennstart (-92 bis +7 Tage) mit , getrennt angeben (yyyy-mm-ttThh:mm), für CSV-Wetter: Input nächste Zeile', 'type': 'text', 'group': 'wetter', 'is_path': False}, {'key': 'field_22', 'index': 22, 'name': 'Wetterdatei Advanced Weather', 'default': 'Wetter_Ironman_70_3_Mallorca_2022_Bike.csv', 'help': 'Input Dateiname inklusive Endung .csv für das Advanced Wettermodell; Daten kann man z.B. bei Meteostat.net finden', 'type': 'text', 'group': 'wetter', 'is_path': True}, {'key': 'field_23', 'index': 23, 'name': 'GPX/FIT Datei', 'default': 'Ironman_70_3_Mallorca_2022_Bike.gpx', 'help': 'Dateiname der GPX-Streckendatei (inklusive Endung .gpx) --> Leistungsinput erfolgt über die angegebenen Leistungsvorgaben   ODER   Dateiname der FIT-Datei (inklusive Endung .fit) --> Leistungsinput kommt aus Fit-Datei', 'type': 'text', 'group': 'strecke', 'is_path': True}, {'key': 'field_24', 'index': 24, 'name': 'Hoehengewinn Sollwert [m]', 'default': 890, 'help': 'Sollhöhengewinn in m, wenn >0 wird Höhenprofil auf Sollhöhe angepasst, wenn <0 wird Höhe aus GPS File verwendet und Hoehendaten_Glaetten=False gestetzt; Bei fit-Datei kann Start- und End Distan in [km] mit Komma angefügt werden', 'type': 'text', 'group': 'strecke', 'is_path': False}, {'key': 'field_25', 'index': 25, 'name': 'min./max.  Steigung in Hoehenprofil [m]', 'default': 25, 'help': 'Steigung der Daten begrenzen, nur wenn Hoehengewinn_Soll>0', 'type': 'float', 'group': 'strecke', 'is_path': False}, {'key': 'field_26', 'index': 26, 'name': 'x-Achse der Plots (Distanz/Zeit)', 'default': 'Distanz', 'help': 'x Achse für die Diagramm Darstellung; Zeit oder Distanz; zur Sicherheit wird alles ungleich Zeit als Distanz angesehen', 'type': 'text', 'group': 'ausgabe', 'is_path': False}, {'key': 'field_27', 'index': 27, 'name': 'Gaus Filter', 'default': 'False', 'help': 'Am Besten nicht Verwenden und auf False stellen', 'type': 'bool', 'group': 'ausgabe', 'is_path': False}, {'key': 'field_28', 'index': 28, 'name': 'Sigma Filter', 'default': 5, 'help': 'Parameter für Gauss-Filter für das Glätten der Diagramme; 1: keine Glättung; je größer, desto stärker ist die Glättung', 'type': 'float', 'group': 'ausgabe', 'is_path': False}, {'key': 'field_29', 'index': 29, 'name': 'Moving Average Filter', 'default': 20, 'help': '20 gibt eine bruachbare Glättung; gibt an wieviele aufeinanderfolgende Datenpunkte gemittelt werden, um einen glatteren Kurvenverlauf zu erhalten', 'type': 'int', 'group': 'ausgabe', 'is_path': False}, {'key': 'field_30', 'index': 30, 'name': 'Anzahl Teilungen in Histogram', 'default': 21, 'help': 'Anzahl der Balken für die Histogram Darstellung', 'type': 'int', 'group': 'ausgabe', 'is_path': False}, {'key': 'field_31', 'index': 31, 'name': 'HTML Karte oeffnen', 'default': 'False', 'help': 'Webbrowser mit HTML Karte direkt öffnen', 'type': 'bool', 'group': 'ausgabe', 'is_path': False}, {'key': 'field_32', 'index': 32, 'name': 'km-Markierungen anzeigen', 'default': 5, 'help': 'Bei einem Wert > 0 wird eine Markierung auf der Karte alles x km angezeit, sonst wird keine Markierung dargestellet', 'type': 'float', 'group': 'ausgabe', 'is_path': False}, {'key': 'field_33', 'index': 33, 'name': 'Plots wahrend der Berechnung zeigen', 'default': 'False', 'help': 'Plots während der Berechnung zusätzlich zum PDF (wird nach berechnung geöffnet) anzeigen', 'type': 'bool', 'group': 'ausgabe', 'is_path': False}, {'key': 'field_34', 'index': 34, 'name': 'Anmerkungen', 'default': '', 'help': '', 'type': 'text', 'group': 'basis', 'is_path': False}]

DATA_NAME: list[str] = [field["name"] for field in FIELDS]
DATA_VALUE_DEFAULT: list[Any] = [field["default"] for field in FIELDS]
DATA_COMMENT: list[str] = [field["help"] for field in FIELDS]


GROUP_TITLES: dict[str, str] = {
    "basis": "🚴 Fahrer & Rad",
    "aero": "💨 Aerodynamik",
    "leistung": "⚡ Leistung",
    "wetter": "🌦 Wetter",
    "strecke": "🗺 Strecke",
    "ausgabe": "📊 Ausgabe",
}


def load_repository_default_input() -> dict[str, Any]:
    """Lädt Default_INPUT.json aus dem Repository, falls vorhanden.

    Dadurch können die Standardwerte ohne Änderung an FIELDS gepflegt werden.
    Fallback ist weiterhin die ursprüngliche Defaultliste aus der Desktop-App.
    """
    import json
    from pathlib import Path

    path = Path(__file__).with_name("Default_INPUT.json")
    if not path.exists():
        return {field["name"]: field["default"] for field in FIELDS}

    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {field["name"]: field["default"] for field in FIELDS}

    defaults = {field["name"]: field["default"] for field in FIELDS}
    for field in FIELDS:
        name = field["name"]
        if name in loaded:
            defaults[name] = loaded[name]
    return defaults


def defaults_dict() -> dict[str, Any]:
    """Defaultwerte als Dict mit den Original-Feldnamen."""
    return load_repository_default_input()


def ordered_values(config: dict[str, Any]) -> list[Any]:
    """Werte in alter Reihenfolge der Tkinter-App zurückgeben."""
    return [config.get(field["name"], field["default"]) for field in FIELDS]


# Felder, die im normalen Workflow häufig gebraucht werden.
# Alle übrigen Parameter bleiben vollständig erhalten und werden unter
# "Erweiterte Einstellungen" angezeigt.
BASIC_FIELD_INDICES: set[int] = {
    0,   # Titel
    1,   # FTP
    2,   # Gewicht Fahrer
    3,   # Gewicht Bike
    4,   # Rollwiderstand
    5,   # cdA flach
    6,   # cdA Berg
    11,  # NP Soll
    12,  # Leistung bei 0 %
    16,  # max. Leistung
    17,  # Temperatur
    18,  # Windgeschwindigkeit
    19,  # Windrichtung
    21,  # Advanced Weather
    23,  # GPX/FIT
    24,  # Höhengewinn
    34,  # Anmerkungen
}


def is_basic_field(field: dict[str, Any]) -> bool:
    return int(field["index"]) in BASIC_FIELD_INDICES


def fields_for_group(group_key: str, basic_only: bool | None = None) -> list[dict[str, Any]]:
    fields = [field for field in FIELDS if field["group"] == group_key]
    if basic_only is True:
        return [field for field in fields if is_basic_field(field)]
    if basic_only is False:
        return [field for field in fields if not is_basic_field(field)]
    return fields
