from __future__ import annotations

import contextlib
import io
import json
import platform
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

import bike_power_calc as bpc
from defaults import FIELDS, GROUP_TITLES, defaults_dict, ordered_values


st.set_page_config(
    page_title="Bike Power Calculator",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_VERSION = "2.1"
BUILD_DATE = "2026-07-10"
ENGINE_VERSION = "1.5.1"

CHANGELOG = {
    "Neu": [
        "Umschaltbarer Entwicklermodus",
        "System- und Ergebnisdiagnose",
        "Projektinformationen und Changelog in der App",
    ],
    "Verbessert": [
        "Laufzeitprofile sind im Normalmodus ausgeblendet",
    ],
    "Behoben": [],
}


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
    if "profile" not in st.session_state:
        st.session_state.profile = None
    if "generate_pdf" not in st.session_state:
        st.session_state.generate_pdf = True
    if "generate_html_map" not in st.session_state:
        st.session_state.generate_html_map = True
    if "last_loaded_json_name" not in st.session_state:
        st.session_state.last_loaded_json_name = None
    if "developer_mode" not in st.session_state:
        st.session_state.developer_mode = False


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




def resolve_repository_path(path_value: str) -> str:
    """Relative Repository-Pfade auf absolute Pfade umsetzen."""
    if not path_value:
        return path_value

    path = Path(path_value)
    if path.is_absolute():
        return str(path)

    candidate = Path(__file__).parent / path
    if candidate.exists():
        return str(candidate)

    return path_value

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


def render_group(group_key: str, config: dict[str, Any]) -> dict[str, Any]:
    result = {}
    group_fields = [field for field in FIELDS if field["group"] == group_key]
    for field in group_fields:
        result[field["name"]] = render_field(field, config)
    return result


# ---------------------------------------------------------------------------
# Adapter from Streamlit config to existing calculation signature
# ---------------------------------------------------------------------------

def bool_from_value(value: Any) -> bool:
    return str(value).lower() == "true" if isinstance(value, str) else bool(value)


def call_bike_power_calc(config: dict[str, Any], generate_pdf: bool = True, generate_html_map: bool = True) -> dict[str, Any]:
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
        generate_pdf,
        generate_html_map,
    )



def get_series(result: dict[str, Any], *names: str) -> list[Any] | None:
    for name in names:
        value = result.get(name)
        if isinstance(value, list) and len(value) > 0:
            return value
    return None


def same_length(x: list[Any], y: list[Any]) -> tuple[list[Any], list[Any]]:
    n = min(len(x), len(y))
    return x[:n], y[:n]


def add_line(fig: go.Figure, result: dict[str, Any], x: list[Any], name: str, *series_names: str, scale: float = 1.0) -> None:
    y = get_series(result, *series_names)
    if y is None:
        return
    xx, yy = same_length(x, y)
    yy = [v * scale if isinstance(v, (int, float)) else v for v in yy]
    fig.add_trace(go.Scatter(x=xx, y=yy, mode="lines", name=name))


def render_interactive_charts(result: dict[str, Any]) -> None:
    """Interaktive Plotly-Diagramme aus den vom Rechner gelieferten Serien."""
    x = get_series(result, "pos")
    x_label = "Distanz [km]"
    if x is None:
        t = get_series(result, "t_cumm")
        if t is None:
            st.info("Für interaktive Diagramme wurden keine Zeit-/Distanzdaten gefunden.")
            return
        x = [v / 60 for v in t]
        x_label = "Zeit [min]"

    st.caption("Interaktive Diagramme: zoomen, Kurven ein-/ausblenden und Werte mit der Maus ablesen.")

    fig1 = go.Figure()
    add_line(fig1, result, x, "Höhe geglättet [m]", "h")
    add_line(fig1, result, x, "Höhe roh [m]", "h_raw")
    add_line(fig1, result, x, "Steigung [%]", "grade")
    fig1.update_layout(
        title="Höhenprofil und Steigung",
        xaxis_title=x_label,
        yaxis_title="Wert",
        hovermode="x unified",
        legend_title="Kurven",
    )
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = go.Figure()
    add_line(fig2, result, x, "Leistung [W]", "power")
    add_line(fig2, result, x, "FIT-Leistung [W]", "Power_fit")
    fig2.update_layout(
        title="Leistung",
        xaxis_title=x_label,
        yaxis_title="Leistung [W]",
        hovermode="x unified",
        legend_title="Kurven",
    )
    if fig2.data:
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Keine Leistungsdaten gefunden.")

    fig3 = go.Figure()
    add_line(fig3, result, x, "Geschwindigkeit [km/h]", "v")
    add_line(fig3, result, x, "Wind effektiv [km/h]", "v_w_List")
    fig3.update_layout(
        title="Geschwindigkeit und Wind",
        xaxis_title=x_label,
        yaxis_title="km/h",
        hovermode="x unified",
        legend_title="Kurven",
    )
    st.plotly_chart(fig3, use_container_width=True)

    fig4 = go.Figure()
    add_line(fig4, result, x, "CdA [m²]", "cdA_List")
    add_line(fig4, result, x, "Luftdichte [kg/m³]", "rho_List")
    fig4.update_layout(
        title="Aerodynamik und Luftdichte",
        xaxis_title=x_label,
        yaxis_title="Wert",
        hovermode="x unified",
        legend_title="Kurven",
    )
    if fig4.data:
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Keine CdA-/Luftdichte-Daten gefunden.")

    weather_available = any(result.get(name) for name in [
        "AdvWeather_TempC", "AdvWeather_AirSpeed", "AdvWeather_AirDir",
        "AdvWeather_AirMoisture", "AdvWeather_AirPressure",
    ])
    if weather_available:
        fig5 = go.Figure()
        add_line(fig5, result, x, "Temperatur [°C]", "AdvWeather_TempC")
        add_line(fig5, result, x, "Wind [km/h]", "AdvWeather_AirSpeed")
        add_line(fig5, result, x, "Windrichtung [°]", "AdvWeather_AirDir")
        add_line(fig5, result, x, "Luftfeuchte [%]", "AdvWeather_AirMoisture")
        add_line(fig5, result, x, "Luftdruck [hPa]", "AdvWeather_AirPressure")
        fig5.update_layout(
            title="Advanced Weather",
            xaxis_title=x_label,
            yaxis_title="Wert",
            hovermode="x unified",
            legend_title="Kurven",
        )
        st.plotly_chart(fig5, use_container_width=True)

    with st.expander("Interaktive Rohdaten anzeigen"):
        data = {"x": x}
        for key in [
            "h", "h_raw", "grade", "power", "Power_fit", "v", "v_w_List",
            "rho_List", "cdA_List", "P_r_rel", "P_g_rel", "P_l_rel", "P_ges", "P_Save",
            "AdvWeather_TempC", "AdvWeather_AirSpeed",
            "AdvWeather_AirDir", "AdvWeather_AirMoisture", "AdvWeather_AirPressure",
        ]:
            series = result.get(key)
            if isinstance(series, list) and series:
                _, yy = same_length(x, series)
                data[key] = yy
        max_len = min(len(v) for v in data.values() if isinstance(v, list))
        data = {k: v[:max_len] if isinstance(v, list) else v for k, v in data.items()}
        st.dataframe(pd.DataFrame(data), use_container_width=True)


def format_seconds(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f} s"


def render_profile(profile: dict[str, float] | None) -> None:
    if not profile:
        return

    st.subheader("Laufzeit-Profil")
    cols = st.columns(4)
    cols[0].metric("Gesamt", format_seconds(profile.get("total_s")))
    cols[1].metric("Berechnung", format_seconds(profile.get("calculation_s")))
    cols[2].metric("Ergebnisaufbereitung", format_seconds(profile.get("postprocess_s")))
    cols[3].metric("Sonstiges", format_seconds(profile.get("other_s")))

    with st.expander("Profiler-Details"):
        rows = [
            {"Abschnitt": "Eingaben prüfen", "Zeit [s]": profile.get("validation_s", 0.0)},
            {"Abschnitt": "Berechnung / PDF / Karte erzeugen", "Zeit [s]": profile.get("calculation_s", 0.0)},
            {"Abschnitt": "Ergebnis in Session speichern", "Zeit [s]": profile.get("postprocess_s", 0.0)},
            {"Abschnitt": "Gesamt", "Zeit [s]": profile.get("total_s", 0.0)},
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

def estimate_result_size_bytes(result: dict[str, Any] | None) -> int:
    """Grobe rekursive Schätzung des Ergebnisobjekts im Arbeitsspeicher."""
    if result is None:
        return 0

    seen: set[int] = set()

    def size_of(value: Any) -> int:
        object_id = id(value)
        if object_id in seen:
            return 0
        seen.add(object_id)

        size = sys.getsizeof(value)
        if isinstance(value, dict):
            size += sum(size_of(k) + size_of(v) for k, v in value.items())
        elif isinstance(value, (list, tuple, set, frozenset)):
            size += sum(size_of(item) for item in value)
        return size

    return size_of(result)


def format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    number = float(value)
    for unit in units:
        if number < 1024 or unit == units[-1]:
            return f"{number:.1f} {unit}"
        number /= 1024
    return f"{value} B"


def render_developer_diagnostics(result: dict[str, Any] | None, profile: dict[str, float] | None) -> None:
    st.subheader("Entwicklerdiagnose")

    point_count = 0
    if result:
        for key in ("pos", "t_cumm", "h", "v", "power"):
            series = result.get(key)
            if isinstance(series, list):
                point_count = max(point_count, len(series))

    cols = st.columns(4)
    cols[0].metric("Streckenpunkte", f"{point_count:,}".replace(",", "."))
    cols[1].metric("Ergebnisgröße", format_bytes(estimate_result_size_bytes(result)))
    cols[2].metric("Python", platform.python_version())
    cols[3].metric("NumPy", np.__version__)

    info_rows = [
        {"Eigenschaft": "App-Version", "Wert": APP_VERSION},
        {"Eigenschaft": "Build", "Wert": BUILD_DATE},
        {"Eigenschaft": "Rechenkern-Basis", "Wert": ENGINE_VERSION},
        {"Eigenschaft": "Streamlit", "Wert": st.__version__},
        {"Eigenschaft": "Pandas", "Wert": pd.__version__},
        {"Eigenschaft": "Betriebssystem", "Wert": platform.platform()},
        {"Eigenschaft": "GPX/FIT-Datei", "Wert": str(st.session_state.config.get("GPX/FIT Datei", ""))},
    ]
    st.dataframe(pd.DataFrame(info_rows), use_container_width=True, hide_index=True)

    render_profile(profile)

    if result:
        steps = result.get("profile_steps")
        if isinstance(steps, list) and steps:
            with st.expander("Detail-Profil der Berechnung", expanded=True):
                df_steps = pd.DataFrame(steps)
                if "Zeit [s]" in df_steps.columns:
                    df_steps["Zeit [s]"] = df_steps["Zeit [s]"].astype(float)
                    st.bar_chart(df_steps.set_index("Abschnitt")["Zeit [s]"])
                st.dataframe(df_steps, use_container_width=True, hide_index=True)

    with st.expander("Changelog Version 2.1"):
        for category, entries in CHANGELOG.items():
            st.markdown(f"**{category}**")
            if entries:
                for entry in entries:
                    st.write(f"✓ {entry}")
            else:
                st.write("–")

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


def render_results(result: dict[str, Any] | None, run_log: str, profile: dict[str, float] | None = None) -> None:
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

    tab_labels = ["📈 Interaktive Diagramme"]
    if pdf_path and pdf_path.exists():
        tab_labels.append("📄 PDF")
    if map_path and map_path.exists():
        tab_labels.append("🗺 Karte")
    tab_labels.append("🧾 Berechnungslog")

    result_tabs = st.tabs(tab_labels)

    tab_index = 0
    with result_tabs[tab_index]:
        render_interactive_charts(result)
    tab_index += 1

    if pdf_path and pdf_path.exists():
        with result_tabs[tab_index]:
            pdf_viewer(pdf_path)
        tab_index += 1

    if map_path and map_path.exists():
        with result_tabs[tab_index]:
            html_map_viewer(map_path)
        tab_index += 1

    with result_tabs[tab_index]:
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
    st.caption(f"Version {APP_VERSION} – stabiler Rechenkern mit optionalem Entwicklermodus")

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
        st.session_state.developer_mode = st.toggle(
            "Entwicklermodus",
            value=st.session_state.developer_mode,
            help="Zeigt Laufzeitprofile, Systeminformationen und Diagnosewerte.",
        )
        st.caption(f"Version {APP_VERSION} · Build {BUILD_DATE}")

    config = st.session_state.config.copy()

    st.subheader("Dateien")
    file_col1, file_col2 = st.columns(2)

    with file_col1:
        route_file = st.file_uploader("GPX/FIT-Datei", type=["gpx", "fit"])
        route_path = save_uploaded_file(route_file)
        if route_path:
            config["GPX/FIT Datei"] = route_path
            st.success(f"Streckendatei geladen: {route_file.name}")
        elif Path(resolve_repository_path(str(config.get("GPX/FIT Datei", "")))).exists():
            st.info(f"Standardstrecke aus Repository aktiv: {config.get('GPX/FIT Datei')}")

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

    st.subheader("Ausgabe")
    out_col1, out_col2 = st.columns(2)
    with out_col1:
        st.session_state.generate_pdf = st.checkbox(
            "PDF erzeugen",
            value=st.session_state.generate_pdf,
            help="Ausschalten spart typischerweise mehrere Sekunden. Download und PDF-Vorschau entfallen dann.",
        )
    with out_col2:
        st.session_state.generate_html_map = st.checkbox(
            "HTML-Karte erzeugen",
            value=st.session_state.generate_html_map,
            help="Ausschalten spart etwas Zeit. Die interaktiven Diagramme bleiben erhalten.",
        )

    run_col, info_col = st.columns([1, 2])

    with run_col:
        start_clicked = st.button("Berechnung starten", type="primary", use_container_width=True)

    with info_col:
        if st.session_state.generate_pdf or st.session_state.generate_html_map:
            st.info("Die Berechnung erzeugt die ausgewählten Ausgaben. Für schnelle Tests kannst du PDF/Karte deaktivieren.")
        else:
            st.info("Schnellmodus aktiv: Es werden nur Berechnung und interaktive Diagramme erzeugt.")

    if start_clicked:
        if not st.session_state.config.get("GPX/FIT Datei"):
            st.error("Bitte zuerst eine GPX- oder FIT-Datei hochladen.")
        else:
            log_buffer = io.StringIO()
            profile: dict[str, float] = {}
            t_total_start = time.perf_counter()
            progress = st.progress(0, text="Berechnung wird vorbereitet …")
            try:
                with st.spinner("Berechnung läuft …"):
                    t_validation_start = time.perf_counter()
                    progress.progress(10, text="Eingaben werden geprüft …")
                    run_config = st.session_state.config.copy()
                    run_config["GPX/FIT Datei"] = resolve_repository_path(str(run_config.get("GPX/FIT Datei", "")))
                    run_config["Wetterdatei Advanced Weather"] = resolve_repository_path(str(run_config.get("Wetterdatei Advanced Weather", "")))
                    profile["validation_s"] = time.perf_counter() - t_validation_start

                    with contextlib.redirect_stdout(log_buffer):
                        progress.progress(25, text="Strecke, Wetter, PDF und Karte werden berechnet …")
                        t_calc_start = time.perf_counter()
                        result = call_bike_power_calc(run_config, st.session_state.generate_pdf, st.session_state.generate_html_map)
                        profile["calculation_s"] = time.perf_counter() - t_calc_start

                    t_post_start = time.perf_counter()
                    progress.progress(100, text="Berechnung abgeschlossen.")
                    st.session_state.result = result
                    st.session_state.run_log = log_buffer.getvalue()
                    profile["postprocess_s"] = time.perf_counter() - t_post_start

                profile["total_s"] = time.perf_counter() - t_total_start
                profile["other_s"] = max(
                    0.0,
                    profile["total_s"] - profile.get("validation_s", 0.0) - profile.get("calculation_s", 0.0) - profile.get("postprocess_s", 0.0),
                )
                st.session_state.profile = profile
                st.success("Berechnung abgeschlossen.")
            except Exception as exc:
                progress.empty()
                profile["total_s"] = time.perf_counter() - t_total_start
                st.session_state.profile = profile
                st.session_state.result = None
                st.session_state.run_log = log_buffer.getvalue() + "\n\nTRACEBACK:\n" + traceback.format_exc()
                st.error(f"Berechnung abgebrochen: {exc}")
                with st.expander("Berechnungslog anzeigen", expanded=True):
                    st.code(st.session_state.run_log)

    render_results(st.session_state.result, st.session_state.run_log, st.session_state.profile)

    if st.session_state.developer_mode:
        render_developer_diagnostics(st.session_state.result, st.session_state.profile)
        with st.expander("Aktuelle Konfiguration anzeigen"):
            st.json(st.session_state.config)

    st.divider()
    st.caption(f"Bike Power Calculator · Version {APP_VERSION} · Build {BUILD_DATE} · Rechenkern {ENGINE_VERSION}")


if __name__ == "__main__":
    main()
