from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

import bike_power_calc as bpc
from defaults import FIELDS, GROUP_TITLES, defaults_dict, ordered_values


st.set_page_config(
    page_title="Bike Power Calculator",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded",
)


def normalize_loaded_config(raw: dict[str, Any]) -> dict[str, Any]:
    config = defaults_dict()
    for field in FIELDS:
        name = field["name"]
        if name in raw:
            config[name] = raw[name]
    return config


def init_session_state() -> None:
    if "config" not in st.session_state:
        st.session_state.config = defaults_dict()
    if "result" not in st.session_state:
        st.session_state.result = None
    if "run_log" not in st.session_state:
        st.session_state.run_log = ""


def save_uploaded_file(uploaded_file) -> str | None:
    if uploaded_file is None:
        return None

    safe_name = Path(uploaded_file.name).name
    temp_dir = Path(tempfile.gettempdir()) / "bike_power_calculator_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    path = temp_dir / safe_name
    path.write_bytes(uploaded_file.getbuffer())
    return str(path)


def render_field(field: dict[str, Any], config: dict[str, Any]) -> Any:
    name = field["name"]
    value = config.get(name, field["default"])
    help_text = field.get("help") or None
    key = f"input_{field['key']}"

    if field["type"] == "bool":
        bool_value = str(value).lower() == "true" if isinstance(value, str) else bool(value)
        return st.checkbox(name, value=bool_value, help=help_text, key=key)

    if field["type"] == "int":
        try:
            int_value = int(value)
        except Exception:
            int_value = int(field["default"])
        return st.number_input(name, value=int_value, step=1, help=help_text, key=key)

    if field["type"] == "float":
        try:
            float_value = float(value)
        except Exception:
            float_value = float(field["default"])
        return st.number_input(name, value=float_value, help=help_text, key=key, format="%.6g")

    return st.text_input(name, value=str(value), help=help_text, key=key)


def render_group(group_key: str, config: dict[str, Any]) -> dict[str, Any]:
    result = {}
    group_fields = [field for field in FIELDS if field["group"] == group_key]
    for field in group_fields:
        result[field["name"]] = render_field(field, config)
    return result


def config_to_json_bytes(config: dict[str, Any]) -> bytes:
    return json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8")


def bool_from_value(value: Any) -> bool:
    return str(value).lower() == "true" if isinstance(value, str) else bool(value)


def call_bike_power_calc(config: dict[str, Any]) -> dict[str, Any]:
    """Übergibt die Streamlit-Konfiguration an die unveränderte Run-Signatur."""
    values = ordered_values(config)

    title = str(values[0])
    ftp = float(values[1])
    m_r = float(values[2])
    m_b = float(values[3])
    cr_dyn = 0
    cr = float(values[4])

    # Parsing wie in der alten Tkinter-Funktion run_bpc()
    import re

    cda_list = [float(s) for s in re.findall(r"-?\d+\.?\d*", str(values[5]))]
    cdA_Flat = cda_list[0]
    Speed_Soll = -1
    if len(cda_list) > 1:
        Speed_Soll = cda_list[1]

    cdA_Hill = float(values[6])
    eta = float(values[7])
    cdA_Hill_Grade = float(values[8])
    Draft_Save_Grade = float(values[9])
    Draft_Save = float(values[10])

    NP_Soll = float(values[11])
    pol_a0 = float(values[12])
    pol_grade_max = float(values[13])
    pol_grade_min = float(values[14])
    power_min = float(values[15])
    power_max_liste = [float(s) for s in re.findall(r"-?\d+\.?\d*", str(values[16]))]

    T_Luft = float(values[17])
    v_w0 = float(values[18])
    dir_w = float(values[19])
    Winddamping = float(values[20])

    weather_parts = str(values[21]).split(",")
    Use_AdvWeather = weather_parts[0] == "True"
    API_Weather = len(weather_parts) > 1 and weather_parts[1] == "True"
    API_StratTime = "2100-01-01T12:00"
    if len(weather_parts) > 2:
        API_StratTime = weather_parts[2]

    Wetterdatei = str(values[22])
    GPX_File = str(values[23])

    height_parts = [float(s) for s in re.findall(r"-?\d+\.?\d*", str(values[24]))]
    Hoehengewinn_Soll = height_parts[0]
    Start_Distance = -1
    End_Distance = 100000
    if len(height_parts) > 2:
        Start_Distance = height_parts[1]
        End_Distance = height_parts[2]

    Steigung_max_min = float(values[25])
    x_Achse = str(values[26])
    Gaus_Filter = bool_from_value(values[27])
    sigma_filter = float(values[28])
    moving_ave_filter = int(values[29])
    Histogram_Anz_Teilungen = int(values[30])
    Open_HTML_Map = False  # In Streamlit nie automatisch Browserfenster öffnen.
    Show_km_Markers = float(values[32])
    Show_Plots_in_Run = False  # In Streamlit/PDF-Modus stabiler.
    Anmerkungen = str(values[34])

    return bpc.Run(
        title,
        m_r,
        m_b,
        cdA_Hill_Grade,
        cdA_Flat,
        Draft_Save_Grade,
        Draft_Save,
        eta,
        cr_dyn,
        cr,
        cdA_Hill,
        ftp,
        power_max_liste,
        NP_Soll,
        pol_a0,
        pol_grade_max,
        power_min,
        pol_grade_min,
        dir_w,
        v_w0,
        T_Luft,
        GPX_File,
        Hoehengewinn_Soll,
        Steigung_max_min,
        sigma_filter,
        x_Achse,
        Histogram_Anz_Teilungen,
        Gaus_Filter,
        moving_ave_filter,
        Open_HTML_Map,
        Show_km_Markers,
        Show_Plots_in_Run,
        Use_AdvWeather,
        API_Weather,
        API_StratTime,
        Wetterdatei,
        Winddamping,
        Anmerkungen,
        Speed_Soll,
        Start_Distance,
        End_Distance,
    )


def render_results(result: dict[str, Any] | None, run_log: str) -> None:
    if not result:
        return

    st.subheader("Ergebnisse")

    cols = st.columns(3)
    distance = result.get("distance_km")
    duration = result.get("duration_s")
    avg_speed = result.get("average_speed_kmh")

    cols[0].metric("Distanz", "—" if distance is None else f"{distance:.2f} km")
    if duration is None:
        cols[1].metric("Zeit", "—")
    else:
        h = int(duration // 3600)
        m = int((duration % 3600) // 60)
        s = int(duration % 60)
        cols[1].metric("Zeit", f"{h:02d}:{m:02d}:{s:02d}")
    cols[2].metric("Ø Geschwindigkeit", "—" if avg_speed is None else f"{avg_speed:.2f} km/h")

    pdf_path = result.get("pdf_path")
    if pdf_path and Path(pdf_path).exists():
        st.download_button(
            "PDF herunterladen",
            data=Path(pdf_path).read_bytes(),
            file_name=Path(pdf_path).name,
            mime="application/pdf",
            use_container_width=True,
        )

    map_path = result.get("map_path")
    if map_path and Path(map_path).exists():
        st.download_button(
            "HTML-Karte herunterladen",
            data=Path(map_path).read_bytes(),
            file_name=Path(map_path).name,
            mime="text/html",
            use_container_width=True,
        )
        with st.expander("HTML-Karte anzeigen"):
            st.components.v1.html(Path(map_path).read_text(encoding="utf-8"), height=600)

    if run_log:
        with st.expander("Berechnungslog anzeigen"):
            st.code(run_log)


def main() -> None:
    init_session_state()

    st.title("🚴 Bike Power Calculator")
    st.caption("Streamlit-Migration der bestehenden Desktop-App – Version 0.3")

    with st.sidebar:
        st.header("Einstellungen")

        uploaded_json = st.file_uploader(
            "JSON-Einstellungen laden",
            type=["json"],
            help="Lädt eine Konfiguration im Format der bisherigen Desktop-App.",
        )

        if uploaded_json is not None:
            try:
                raw_config = json.load(uploaded_json)
                st.session_state.config = normalize_loaded_config(raw_config)
                st.success("JSON-Einstellungen geladen.")
            except Exception as exc:
                st.error(f"JSON konnte nicht geladen werden: {exc}")

        st.download_button(
            "Aktuelle Einstellungen herunterladen",
            data=config_to_json_bytes(st.session_state.config),
            file_name="BikePowerCalculator_INPUT.json",
            mime="application/json",
        )

        st.divider()
        st.success("Version 0.3: Berechnung angebunden.")

    config = st.session_state.config.copy()

    st.subheader("Dateien")
    file_col1, file_col2 = st.columns(2)

    with file_col1:
        route_file = st.file_uploader("GPX/FIT-Datei", type=["gpx", "fit"])
        route_path = save_uploaded_file(route_file)
        if route_path:
            config["GPX/FIT Datei"] = route_path
            st.success(f"Streckendatei geladen: {route_file.name}")

    with file_col2:
        weather_file = st.file_uploader("Wetterdatei Advanced Weather", type=["csv"])
        weather_path = save_uploaded_file(weather_file)
        if weather_path:
            config["Wetterdatei Advanced Weather"] = weather_path
            st.success(f"Wetterdatei geladen: {weather_file.name}")

    tab_keys = ["basis", "aero", "leistung", "wetter", "strecke", "ausgabe"]
    tabs = st.tabs([GROUP_TITLES[key] for key in tab_keys])

    updated = {}
    for tab, group_key in zip(tabs, tab_keys):
        with tab:
            updated.update(render_group(group_key, config))

    if route_path:
        updated["GPX/FIT Datei"] = route_path
    if weather_path:
        updated["Wetterdatei Advanced Weather"] = weather_path

    st.session_state.config = normalize_loaded_config(updated)

    st.divider()

    if st.button("Berechnung starten", type="primary", use_container_width=True):
        if not st.session_state.config.get("GPX/FIT Datei"):
            st.error("Bitte zuerst eine GPX- oder FIT-Datei hochladen.")
        else:
            log_buffer = io.StringIO()
            try:
                with st.spinner("Berechnung läuft …"):
                    with contextlib.redirect_stdout(log_buffer):
                        result = call_bike_power_calc(st.session_state.config)
                st.session_state.result = result
                st.session_state.run_log = log_buffer.getvalue()
                st.success("Berechnung abgeschlossen.")
            except Exception as exc:
                st.session_state.run_log = log_buffer.getvalue()
                st.error(f"Berechnung abgebrochen: {exc}")
                with st.expander("Berechnungslog anzeigen"):
                    st.code(st.session_state.run_log)

    render_results(st.session_state.result, st.session_state.run_log)

    with st.expander("Aktuelle Konfiguration anzeigen"):
        st.json(st.session_state.config)


if __name__ == "__main__":
    main()
