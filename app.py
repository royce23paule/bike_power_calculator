from __future__ import annotations

import contextlib
import io
import json
import tempfile
import traceback
from pathlib import Path
from typing import Any

import streamlit as st

import bike_power_calc as bpc
from defaults import FIELDS, GROUP_TITLES, defaults_dict, fields_for_group, ordered_values


st.set_page_config(
    page_title="Bike Power Calculator",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Session State / JSON
# ---------------------------------------------------------------------------

def widget_key(field: dict[str, Any]) -> str:
    return f"input_{field['key']}"


def normalize_loaded_config(raw: dict[str, Any]) -> dict[str, Any]:
    config = defaults_dict()
    for field in FIELDS:
        name = field["name"]
        if name in raw:
            config[name] = raw[name]
    return config


def sync_widgets_from_config(config: dict[str, Any]) -> None:
    for field in FIELDS:
        key = widget_key(field)
        value = config.get(field["name"], field["default"])

        if field["type"] == "bool":
            value = str(value).lower() == "true" if isinstance(value, str) else bool(value)
        elif field["type"] == "int":
            try:
                value = int(value)
            except Exception:
                value = int(field["default"])
        elif field["type"] == "float":
            try:
                value = float(value)
            except Exception:
                value = float(field["default"])
        else:
            value = str(value)

        st.session_state[key] = value


def init_session_state() -> None:
    if "config" not in st.session_state:
        st.session_state.config = defaults_dict()
    if "result" not in st.session_state:
        st.session_state.result = None
    if "run_log" not in st.session_state:
        st.session_state.run_log = ""
    if "last_loaded_json_name" not in st.session_state:
        st.session_state.last_loaded_json_name = None


def config_to_json_bytes(config: dict[str, Any]) -> bytes:
    return json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8")


# ---------------------------------------------------------------------------
# Uploads / UI widgets
# ---------------------------------------------------------------------------

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
    key = widget_key(field)

    if field["type"] == "bool":
        if key not in st.session_state:
            st.session_state[key] = str(value).lower() == "true" if isinstance(value, str) else bool(value)
        return st.checkbox(name, help=help_text, key=key)

    if field["type"] == "int":
        if key not in st.session_state:
            try:
                st.session_state[key] = int(value)
            except Exception:
                st.session_state[key] = int(field["default"])
        return st.number_input(name, step=1, help=help_text, key=key)

    if field["type"] == "float":
        if key not in st.session_state:
            try:
                st.session_state[key] = float(value)
            except Exception:
                st.session_state[key] = float(field["default"])
        return st.number_input(name, help=help_text, key=key, format="%.6g")

    if key not in st.session_state:
        st.session_state[key] = str(value)
    return st.text_input(name, help=help_text, key=key)


def render_group_fields(fields: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for field in fields:
        result[field["name"]] = render_field(field, config)
    return result


def render_compact_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Kompakte Oberfläche für den normalen Workflow."""
    result = {}

    st.subheader("Basisparameter")
    st.caption("Die wichtigsten Eingaben für eine schnelle Berechnung. Alle weiteren Optionen bleiben unten im Expertenbereich verfügbar.")

    basis_cols = st.columns(3)
    basis_map = {
        0: basis_cols[0],
        1: basis_cols[1],
        11: basis_cols[2],
        2: basis_cols[0],
        3: basis_cols[1],
        4: basis_cols[2],
    }
    for field in FIELDS:
        if field["index"] in basis_map:
            with basis_map[field["index"]]:
                result[field["name"]] = render_field(field, config)

    st.subheader("Aerodynamik & Leistung")
    aero_cols = st.columns(3)
    aero_map = {
        5: aero_cols[0],
        6: aero_cols[1],
        12: aero_cols[2],
        16: aero_cols[2],
    }
    for field in FIELDS:
        if field["index"] in aero_map:
            with aero_map[field["index"]]:
                result[field["name"]] = render_field(field, config)

    st.subheader("Wetter & Strecke")
    route_cols = st.columns(3)
    route_map = {
        17: route_cols[0],
        18: route_cols[1],
        19: route_cols[2],
        21: route_cols[0],
        23: route_cols[1],
        24: route_cols[2],
    }
    for field in FIELDS:
        if field["index"] in route_map:
            with route_map[field["index"]]:
                result[field["name"]] = render_field(field, config)

    st.subheader("Notizen")
    for field in FIELDS:
        if field["index"] == 34:
            result[field["name"]] = render_field(field, config)

    return result


def render_expert_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Alle selten benötigten Parameter, weiterhin vollständig editierbar."""
    result = {}
    tab_keys = ["basis", "aero", "leistung", "wetter", "strecke", "ausgabe"]
    tabs = st.tabs([GROUP_TITLES[key] for key in tab_keys])

    for tab, group_key in zip(tabs, tab_keys):
        with tab:
            expert_fields = fields_for_group(group_key, basic_only=False)
            if not expert_fields:
                st.info("Keine zusätzlichen Expertenparameter in diesem Bereich.")
            else:
                result.update(render_group_fields(expert_fields, config))

    return result


# ---------------------------------------------------------------------------
# Adapter from Streamlit config to existing calculation signature
# ---------------------------------------------------------------------------

def bool_from_value(value: Any) -> bool:
    return str(value).lower() == "true" if isinstance(value, str) else bool(value)


def call_bike_power_calc(config: dict[str, Any]) -> dict[str, Any]:
    values = ordered_values(config)

    title = str(values[0])
    ftp = float(values[1])
    m_r = float(values[2])
    m_b = float(values[3])
    cr_dyn = 0
    cr = float(values[4])

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
    Open_HTML_Map = False
    Show_km_Markers = float(values[32])
    Show_Plots_in_Run = False
    Anmerkungen = str(values[34])

    if not Path(GPX_File).exists():
        raise FileNotFoundError(f"GPX/FIT-Datei nicht gefunden: {GPX_File}")

    if Use_AdvWeather and not API_Weather and not Path(Wetterdatei).exists():
        raise FileNotFoundError(f"Wetter-CSV nicht gefunden: {Wetterdatei}")

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


# ---------------------------------------------------------------------------
# Result rendering
# ---------------------------------------------------------------------------

def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def pdf_viewer(pdf_path: Path, max_pages: int = 12) -> None:
    """PDF-Vorschau als Bilder rendern.

    Ein eingebettetes PDF per iframe/data-URL wird von Chrome in manchen
    Streamlit-Umgebungen blockiert. PyMuPDF rendert die PDF-Seiten als PNGs,
    was deutlich robuster ist.
    """
    try:
        import fitz  # PyMuPDF
    except Exception:
        st.info(
            "PDF-Vorschau benötigt PyMuPDF. Der PDF-Download funktioniert trotzdem. "
            "Bitte `pymupdf` in requirements.txt installieren."
        )
        return

    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        pages_to_show = min(total_pages, max_pages)

        st.caption(
            f"Vorschau: {pages_to_show} von {total_pages} Seiten. "
            "Die vollständige PDF steht oben als Download bereit."
        )

        zoom = st.slider("PDF-Vorschau Zoom", 1.0, 3.0, 1.6, 0.1)
        matrix = fitz.Matrix(zoom, zoom)

        for page_number in range(pages_to_show):
            page = doc.load_page(page_number)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image_bytes = pix.tobytes("png")
            st.image(image_bytes, caption=f"PDF-Seite {page_number + 1}", use_container_width=True)

        if total_pages > max_pages:
            st.info("Weitere Seiten sind in der herunterladbaren PDF enthalten.")

    except Exception as exc:
        st.info(f"PDF-Vorschau konnte nicht gerendert werden: {exc}")


def html_map_viewer(map_path: Path, height: int = 650) -> None:
    try:
        st.components.v1.html(map_path.read_text(encoding="utf-8"), height=height)
    except UnicodeDecodeError:
        st.components.v1.html(map_path.read_text(encoding="latin-1"), height=height)


def render_results(result: dict[str, Any] | None, run_log: str) -> None:
    if not result:
        return

    st.subheader("Ergebnisse")

    distance = result.get("distance_km")
    duration = result.get("duration_s")
    avg_speed = result.get("average_speed_kmh")

    metric_cols = st.columns(4)
    metric_cols[0].metric("Titel", result.get("title", "—"))
    metric_cols[1].metric("Distanz", "—" if distance is None else f"{distance:.2f} km")
    metric_cols[2].metric("Zeit", format_duration(duration))
    metric_cols[3].metric("Ø Geschwindigkeit", "—" if avg_speed is None else f"{avg_speed:.2f} km/h")

    pdf_path_value = result.get("pdf_path")
    map_path_value = result.get("map_path")

    pdf_path = Path(pdf_path_value) if pdf_path_value else None
    map_path = Path(map_path_value) if map_path_value else None

    download_cols = st.columns(2)

    with download_cols[0]:
        if pdf_path and pdf_path.exists():
            st.download_button(
                "PDF herunterladen",
                data=pdf_path.read_bytes(),
                file_name=pdf_path.name,
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.info("Keine PDF-Datei gefunden.")

    with download_cols[1]:
        if map_path and map_path.exists():
            st.download_button(
                "HTML-Karte herunterladen",
                data=map_path.read_bytes(),
                file_name=map_path.name,
                mime="text/html",
                use_container_width=True,
            )
        else:
            st.info("Keine HTML-Karte gefunden.")

    result_tabs = st.tabs(["📄 PDF", "🗺 Karte", "🧾 Berechnungslog"])

    with result_tabs[0]:
        if pdf_path and pdf_path.exists():
            pdf_viewer(pdf_path)
        else:
            st.warning("PDF-Vorschau nicht verfügbar.")

    with result_tabs[1]:
        if map_path and map_path.exists():
            html_map_viewer(map_path)
        else:
            st.warning("Karte nicht verfügbar.")

    with result_tabs[2]:
        if run_log:
            st.code(run_log)
        else:
            st.info("Kein Berechnungslog vorhanden.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    init_session_state()

    st.title("🚴 Bike Power Calculator")
    st.caption("Streamlit-Migration der bestehenden Desktop-App – Version 0.7")
    st.markdown(
        """
        <style>
        .stMetric { border: 1px solid rgba(49, 51, 63, 0.15); border-radius: 0.75rem; padding: 0.75rem; }
        div[data-testid="stExpander"] { border-radius: 0.75rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Einstellungen")

        uploaded_json = st.file_uploader(
            "JSON-Einstellungen laden",
            type=["json"],
            help="Lädt eine Konfiguration im Format der bisherigen Desktop-App.",
        )

        if uploaded_json is not None:
            if uploaded_json.name != st.session_state.last_loaded_json_name:
                try:
                    raw_config = json.load(uploaded_json)
                    loaded_config = normalize_loaded_config(raw_config)
                    st.session_state.config = loaded_config
                    sync_widgets_from_config(loaded_config)
                    st.session_state.last_loaded_json_name = uploaded_json.name
                    st.success("JSON-Einstellungen geladen und übernommen.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"JSON konnte nicht geladen werden: {exc}")

        st.download_button(
            "Aktuelle Einstellungen herunterladen",
            data=config_to_json_bytes(st.session_state.config),
            file_name="BikePowerCalculator_INPUT.json",
            mime="application/json",
            use_container_width=True,
        )

        st.divider()
        st.success("Version 0.7: kompakte Oberfläche + Expertenmodus.")

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

    updated = {}

    input_mode = st.radio(
        "Eingabeansicht",
        ["Kompakt", "Experte"],
        horizontal=True,
        help="Kompakt zeigt die wichtigsten Felder. Experte zeigt alle übrigen Parameter.",
    )

    if input_mode == "Kompakt":
        updated.update(render_compact_inputs(config))
        with st.expander("⚙ Erweiterte Einstellungen", expanded=False):
            updated.update(render_expert_inputs(config))
    else:
        st.subheader("Alle Einstellungen")
        updated.update(render_group_fields(FIELDS, config))

    if route_path:
        updated["GPX/FIT Datei"] = route_path
    if weather_path:
        updated["Wetterdatei Advanced Weather"] = weather_path

    # Felder, die in der gewählten Ansicht nicht gerendert wurden, behalten ihren bisherigen Wert.
    merged_config = config.copy()
    merged_config.update(updated)
    st.session_state.config = normalize_loaded_config(merged_config)

    st.divider()

    run_col, info_col = st.columns([1, 2])

    with run_col:
        start_clicked = st.button("Berechnung starten", type="primary", use_container_width=True)

    with info_col:
        st.info("Die Berechnung kann je nach Streckenlänge und Wettermodell etwas dauern. Danach erscheinen PDF, Karte und Log direkt unten.")

    if start_clicked:
        if not st.session_state.config.get("GPX/FIT Datei"):
            st.error("Bitte zuerst eine GPX- oder FIT-Datei hochladen.")
        else:
            log_buffer = io.StringIO()
            progress = st.progress(0, text="Berechnung wird vorbereitet …")
            try:
                with st.spinner("Berechnung läuft …"):
                    progress.progress(10, text="Eingaben werden geprüft …")
                    with contextlib.redirect_stdout(log_buffer):
                        progress.progress(25, text="Strecke und Wetter werden verarbeitet …")
                        result = call_bike_power_calc(st.session_state.config)
                    progress.progress(100, text="Berechnung abgeschlossen.")
                st.session_state.result = result
                st.session_state.run_log = log_buffer.getvalue()
                st.success("Berechnung abgeschlossen.")
            except Exception as exc:
                progress.empty()
                st.session_state.result = None
                st.session_state.run_log = log_buffer.getvalue() + "\n\nTRACEBACK:\n" + traceback.format_exc()
                st.error(f"Berechnung abgebrochen: {exc}")
                with st.expander("Berechnungslog anzeigen", expanded=True):
                    st.code(st.session_state.run_log)

    render_results(st.session_state.result, st.session_state.run_log)

    with st.expander("Aktuelle Konfiguration anzeigen"):
        st.json(st.session_state.config)


if __name__ == "__main__":
    main()
