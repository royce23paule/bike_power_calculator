from __future__ import annotations

import contextlib
import io
import json
import shutil
import uuid
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
import pydeck as pdk
from plotly.subplots import make_subplots

import bike_power_calc as bpc
from github_database import GitHubDatabase, GitHubDatabaseConfig, GitHubDatabaseError
from defaults import FIELDS, GROUP_TITLES, defaults_dict, ordered_values
import re
from datetime import datetime


st.set_page_config(
    page_title="Bike Power Calculator",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    .stAppViewContainer .main .block-container,
    section.main > div.block-container,
    div[data-testid="stMainBlockContainer"] {
        max-width: 100% !important;
        width: 100% !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }

    div[data-testid="stVerticalBlock"],
    div[data-testid="stHorizontalBlock"],
    div[data-testid="column"] {
        width: 100%;
        max-width: 100%;
    }

    div[data-testid="stDataFrame"],
    div[data-testid="stPlotlyChart"],
    div[data-testid="stExpander"],
    div[data-testid="stMetric"] {
        max-width: 100% !important;
    }

    @media (max-width: 900px) {
        .stAppViewContainer .main .block-container,
        section.main > div.block-container,
        div[data-testid="stMainBlockContainer"] {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

APP_VERSION = "3.4.1"
BUILD_DATE = "2026-07-14"
ENGINE_VERSION = "1.5.1-cache-benchmark"

CHANGELOG = {
    "Neu": [
        "Automatischer Vergleich aktueller Ergebnisse mit der API-Benchmarkreferenz",
        "Persistenter Cache für Open-Meteo-API-Abfragen",
        "Manueller Neuabruf der Online-Wetterdaten",
        "System- und Ergebnisdiagnose",
        "Projektinformationen und Changelog in der App",
    ],
    "Verbessert": [
        "Wiederholungsberechnungen mit identischer Strecke/Startzeit nutzen lokale Wetterdaten",
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
        st.session_state.generate_pdf = False
    if "generate_html_map" not in st.session_state:
        st.session_state.generate_html_map = False
    if "last_loaded_json_name" not in st.session_state:
        st.session_state.last_loaded_json_name = None
    if "developer_mode" not in st.session_state:
        st.session_state.developer_mode = False
    if "refresh_weather_cache" not in st.session_state:
        st.session_state.refresh_weather_cache = False


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

    weather_suffix = Path(Wetterdatei).suffix.lower()
    if Use_AdvWeather and weather_suffix == ".json":
        API_Weather = True
    if Use_AdvWeather and weather_suffix in {".csv", ".json"} and not Path(Wetterdatei).exists():
        raise FileNotFoundError(f"Wetterdatei nicht gefunden: {Wetterdatei}")
    if Use_AdvWeather and not API_Weather and weather_suffix != ".csv":
        raise ValueError("Für das CSV-Wettermodell muss eine CSV-Datei ausgewählt sein.")

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
    with st.expander("Vollständige interaktive Auswertung anzeigen", expanded=False):
        render_full_interactive_report(result)


def _unique_dataframe_columns(columns: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    result = []
    for index, column in enumerate(columns):
        name = str(column).strip() or f"Spalte {index + 1}"
        counts[name] = counts.get(name, 0) + 1
        if counts[name] > 1:
            name = f"{name} ({counts[name]})"
        result.append(name)
    return result


def render_serialized_report_chart(item: dict[str, Any]) -> None:
    series = item.get("series")
    if not isinstance(series, list) or not series:
        st.info("Keine darstellbaren Diagrammdaten vorhanden.")
        return

    secondary_axis = any(int(entry.get("axis", 0)) > 0 for entry in series)
    figure = make_subplots(specs=[[{"secondary_y": secondary_axis}]])
    primary_label = None
    secondary_label = None

    for entry in series:
        x_values = entry.get("x", [])
        y_values = entry.get("y", [])
        if not x_values or not y_values:
            continue

        secondary = int(entry.get("axis", 0)) > 0
        y_label = entry.get("y_label") or "Wert"
        if secondary:
            secondary_label = secondary_label or y_label
        else:
            primary_label = primary_label or y_label

        if entry.get("type") == "bar":
            trace = go.Bar(x=x_values, y=y_values, name=entry.get("name", "Verteilung"))
        else:
            trace = go.Scatter(
                x=x_values,
                y=y_values,
                mode="lines",
                name=entry.get("name", "Wert"),
            )
        figure.add_trace(trace, secondary_y=secondary)

    figure.update_layout(
        title=item.get("title", "Diagramm"),
        xaxis_title=item.get("x_label", ""),
        hovermode="x unified",
        legend_title="Kurven",
        height=520,
    )
    if primary_label:
        figure.update_yaxes(title_text=primary_label, secondary_y=False)
    if secondary_axis and secondary_label:
        figure.update_yaxes(title_text=secondary_label, secondary_y=True)
    st.plotly_chart(figure, use_container_width=True)


def render_serialized_report_table(item: dict[str, Any]) -> None:
    rows = item.get("rows", [])
    columns = item.get("columns", [])
    if not rows:
        st.info("Keine Tabellendaten vorhanden.")
        return

    width = max(len(row) for row in rows)
    normalized = [list(row) + [""] * (width - len(row)) for row in rows]
    first_row = normalized[0]
    use_header = (
        len(normalized) > 1
        and all(str(value).strip() for value in first_row)
        and any(not str(value).replace(".", "", 1).replace("-", "", 1).isdigit() for value in first_row)
    )

    if use_header:
        dataframe_columns = _unique_dataframe_columns([str(value) for value in first_row])
        dataframe_rows = normalized[1:]
    else:
        if len(columns) != width:
            columns = [f"Spalte {index + 1}" for index in range(width)]
        dataframe_columns = _unique_dataframe_columns(columns)
        dataframe_rows = normalized

    st.dataframe(
        pd.DataFrame(dataframe_rows, columns=dataframe_columns),
        use_container_width=True,
        hide_index=True,
    )



def _normalize_map_values(values: list[float]) -> list[float]:
    numeric = np.asarray(values, dtype=float)
    finite = np.isfinite(numeric)
    if not finite.any():
        return [0.5] * len(numeric)

    low = float(np.nanpercentile(numeric[finite], 5))
    high = float(np.nanpercentile(numeric[finite], 95))
    if high <= low:
        return [0.5] * len(numeric)

    normalized = (numeric - low) / (high - low)
    normalized = np.clip(normalized, 0.0, 1.0)
    normalized[~finite] = 0.5
    return normalized.tolist()


def _color_from_normalized(value: float) -> list[int]:
    value = max(0.0, min(1.0, float(value)))
    # Blau -> Türkis -> Gelb -> Rot
    if value < 0.33:
        fraction = value / 0.33
        red = int(30 + 20 * fraction)
        green = int(90 + 140 * fraction)
        blue = int(220 - 80 * fraction)
    elif value < 0.66:
        fraction = (value - 0.33) / 0.33
        red = int(50 + 200 * fraction)
        green = int(230 - 20 * fraction)
        blue = int(140 - 100 * fraction)
    else:
        fraction = (value - 0.66) / 0.34
        red = 250
        green = int(210 - 160 * fraction)
        blue = int(40 - 20 * fraction)
    return [red, green, blue, 220]


def _bearing_endpoint(lat: float, lon: float, bearing_deg: float, length_deg: float) -> tuple[float, float]:
    bearing = np.deg2rad(float(bearing_deg))
    dlat = np.cos(bearing) * length_deg
    dlon = np.sin(bearing) * length_deg / max(np.cos(np.deg2rad(lat)), 0.2)
    return lat + dlat, lon + dlon


def render_colored_track_map(result: dict[str, Any]) -> None:
    lat = result.get("map_latitude")
    lon = result.get("map_longitude")
    distance = result.get("map_distance_km")
    if not isinstance(lat, list) or not isinstance(lon, list):
        st.info("Für diesen Lauf sind keine GPS-Daten verfügbar.")
        return

    metrics = {
        "Geschwindigkeit [km/h]": result.get("map_speed_kmh"),
        "Leistung [W]": result.get("map_power_w"),
        "Windgeschwindigkeit [km/h]": result.get("map_wind_kmh"),
        "Windkomponente längs [km/h]": result.get("map_wind_component_kmh"),
        "Relative Luftgeschwindigkeit [km/h]": result.get("map_air_speed_kmh"),
        "Höhe [m]": result.get("map_elevation_m"),
        "Steigung [%]": result.get("map_grade_percent"),
    }
    metrics = {
        name: values for name, values in metrics.items()
        if isinstance(values, list) and len(values) > 1
    }

    # Höhe explizit ergänzen, falls sie vorhanden ist, aber wegen einer
    # abweichenden Länge zuvor herausgefiltert wurde.
    elevation_values = result.get("map_elevation_m")
    if isinstance(elevation_values, list) and len(elevation_values) > 1:
        metrics["Höhe [m]"] = elevation_values
    if not metrics:
        st.info("Für die Karteneinfärbung stehen keine Messreihen zur Verfügung.")
        return

    control_cols = st.columns([2, 1, 1])
    with control_cols[0]:
        selected_metric = st.selectbox(
            "Track einfärben nach",
            list(metrics.keys()),
            index=0,
            key="track_map_metric",
        )
    with control_cols[1]:
        show_wind_arrows = st.checkbox(
            "Windrichtungspfeile",
            value=True,
            key="track_map_wind_arrows",
        )
    with control_cols[2]:
        arrow_spacing_km = st.number_input(
            "Pfeilabstand [km]",
            min_value=0.5,
            max_value=20.0,
            value=2.0,
            step=0.5,
            disabled=not show_wind_arrows,
            key="track_map_arrow_spacing",
        )

    values = metrics[selected_metric]
    n = min(len(lat), len(lon))
    if isinstance(distance, list):
        n = min(n, len(distance))
    n = min(n, len(values))
    if n < 2:
        st.info("Zu wenige GPS-Punkte für die Kartenanzeige.")
        return

    lat = [float(value) for value in lat[:n]]
    lon = [float(value) for value in lon[:n]]
    values = [float(value) for value in values[:n]]
    if isinstance(distance, list):
        distance_values = [float(value) for value in distance[:n]]
    else:
        distance_values = list(np.linspace(0.0, float(n - 1), n))

    normalized = _normalize_map_values(values)

    all_speed = result.get("map_speed_kmh")
    all_power = result.get("map_power_w")
    all_wind = result.get("map_wind_kmh")
    all_wind_component = result.get("map_wind_component_kmh")
    all_air_speed = result.get("map_air_speed_kmh")
    all_elevation = result.get("map_elevation_m")
    all_grade = result.get("map_grade_percent")
    all_wind_direction = result.get("map_wind_direction_deg")

    def value_at(series, index, default=None):
        if not isinstance(series, list) or not series:
            return default

        safe_index = min(max(int(index), 0), len(series) - 1)
        try:
            value = float(series[safe_index])
            return value if np.isfinite(value) else default
        except (TypeError, ValueError):
            return default

    def format_tooltip_value(value) -> str:
        if value is None:
            return "—"
        try:
            numeric = float(value)
            if not np.isfinite(numeric):
                return "—"
            return f"{numeric:.2f}"
        except (TypeError, ValueError):
            return "—"

    segments = []
    for index in range(n - 1):
        segments.append({
            "path": [[lon[index], lat[index]], [lon[index + 1], lat[index + 1]]],
            "color": _color_from_normalized((normalized[index] + normalized[index + 1]) / 2),
            "value": f"{((values[index] + values[index + 1]) / 2):.2f}",
            "metric": selected_metric,
            "distance": f"{distance_values[index]:.2f}",
            "speed": format_tooltip_value(value_at(all_speed, index)),
            "power": format_tooltip_value(value_at(all_power, index)),
            "wind_speed": format_tooltip_value(value_at(all_wind, index)),
            "wind_component": format_tooltip_value(value_at(all_wind_component, index)),
            "air_speed": format_tooltip_value(value_at(all_air_speed, index)),
            "elevation": format_tooltip_value(value_at(all_elevation, index)),
            "grade": format_tooltip_value(value_at(all_grade, index)),
            "wind_direction": format_tooltip_value(value_at(all_wind_direction, index)),
        })

    layers = [
        pdk.Layer(
            "PathLayer",
            data=segments,
            get_path="path",
            get_color="color",
            width_scale=1,
            width_min_pixels=4,
            pickable=True,
            auto_highlight=True,
        )
    ]

    # Start and finish markers.
    markers = [
        {"position": [lon[0], lat[0]], "label": "Start"},
        {"position": [lon[-1], lat[-1]], "label": "Ziel"},
    ]
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=markers,
            get_position="position",
            get_radius=35,
            get_fill_color=[255, 255, 255, 230],
            get_line_color=[0, 0, 0, 255],
            line_width_min_pixels=2,
            stroked=True,
            pickable=True,
        )
    )

    if show_wind_arrows:
        wind_direction = result.get("map_wind_direction_deg")
        wind_speed = result.get("map_wind_kmh")

        if isinstance(wind_direction, list) and isinstance(wind_speed, list):
            arrow_n = min(n, len(wind_direction), len(wind_speed))
            shafts = []
            heads = []
            next_distance = max(float(arrow_spacing_km) * 0.5, 0.25)

            for index in range(1, max(1, arrow_n - 1)):
                if distance_values[index] + 1e-9 < next_distance:
                    continue

                try:
                    direction_value = float(wind_direction[index])
                    speed_value = abs(float(wind_speed[index]))
                    latitude_value = float(lat[index])
                    longitude_value = float(lon[index])
                except (TypeError, ValueError):
                    continue

                if not (
                    np.isfinite(direction_value)
                    and np.isfinite(speed_value)
                    and np.isfinite(latitude_value)
                    and np.isfinite(longitude_value)
                ):
                    continue

                # Der Pfeil zeigt in die meteorologische Windrichtung:
                # dorthin, woher der Wind kommt.
                flow_direction = direction_value % 360.0

                # Feste, gut sichtbare Pfeillänge; nur leicht abhängig von Windstärke.
                shaft_length = 0.0018 + min(speed_value, 40.0) / 40.0 * 0.0012
                end_lat, end_lon = _bearing_endpoint(
                    latitude_value,
                    longitude_value,
                    flow_direction,
                    shaft_length,
                )

                # Pfeilspitzen relativ zum Schaft.
                head_length = shaft_length * 0.35
                left_lat, left_lon = _bearing_endpoint(
                    end_lat,
                    end_lon,
                    (flow_direction + 150.0) % 360.0,
                    head_length,
                )
                right_lat, right_lon = _bearing_endpoint(
                    end_lat,
                    end_lon,
                    (flow_direction - 150.0) % 360.0,
                    head_length,
                )

                common = {
                    "wind_speed": format_tooltip_value(speed_value),
                    "wind_direction": format_tooltip_value(direction_value),
                    "distance": f"{distance_values[index]:.2f}",
                    "metric": "Wind",
                    "value": format_tooltip_value(speed_value),
                    "speed": format_tooltip_value(value_at(all_speed, index)),
                    "power": format_tooltip_value(value_at(all_power, index)),
                    "wind_component": format_tooltip_value(value_at(all_wind_component, index)),
                    "air_speed": format_tooltip_value(value_at(all_air_speed, index)),
                    "elevation": format_tooltip_value(value_at(all_elevation, index)),
                    "grade": format_tooltip_value(value_at(all_grade, index)),
                }

                shafts.append({
                    **common,
                    "source": [longitude_value, latitude_value],
                    "target": [end_lon, end_lat],
                })
                heads.append({
                    **common,
                    "source": [end_lon, end_lat],
                    "target": [left_lon, left_lat],
                })
                heads.append({
                    **common,
                    "source": [end_lon, end_lat],
                    "target": [right_lon, right_lat],
                })

                next_distance = distance_values[index] + float(arrow_spacing_km)

            if shafts:
                layers.append(
                    pdk.Layer(
                        "LineLayer",
                        data=shafts,
                        get_source_position="source",
                        get_target_position="target",
                        get_color=[20, 20, 20, 235],
                        get_width=4,
                        width_min_pixels=3,
                        pickable=True,
                    )
                )
                layers.append(
                    pdk.Layer(
                        "LineLayer",
                        data=heads,
                        get_source_position="source",
                        get_target_position="target",
                        get_color=[20, 20, 20, 235],
                        get_width=4,
                        width_min_pixels=3,
                        pickable=True,
                    )
                )

    center_lat = float(np.nanmean(lat))
    center_lon = float(np.nanmean(lon))
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=10,
        pitch=0,
    )

    tooltip = {
        "html": (
            "<b>{metric}</b>: {value}<br/>"
            "Distanz: {distance} km<hr style='margin:4px 0'>"
            "Geschwindigkeit: {speed} km/h<br/>"
            "Leistung: {power} W<br/>"
            "Windgeschwindigkeit: {wind_speed} km/h<br/>"
            "Windkomponente längs: {wind_component} km/h<br/>"
            "Relative Luftgeschwindigkeit: {air_speed} km/h<br/>"
            "Windrichtung: {wind_direction}°<br/>"
            "Höhe: {elevation} m<br/>"
            "Steigung: {grade} %"
        ),
        "style": {
            "backgroundColor": "rgba(20,20,20,0.92)",
            "color": "white",
            "fontSize": "0.85rem",
        },
    }

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=None,
        tooltip=tooltip,
    )
    st.pydeck_chart(deck, use_container_width=True)

    values_array = np.asarray(values, dtype=float)
    finite_values = values_array[np.isfinite(values_array)]

    if finite_values.size:
        scale_min = float(np.nanpercentile(finite_values, 5))
        scale_max = float(np.nanpercentile(finite_values, 95))
        st.markdown(
            f"""
            <div style="margin-top:0.5rem; margin-bottom:0.75rem;">
                <div style="
                    height:18px;
                    border-radius:9px;
                    background:linear-gradient(
                        90deg,
                        rgb(30,90,220) 0%,
                        rgb(50,230,140) 33%,
                        rgb(250,210,40) 66%,
                        rgb(250,50,20) 100%
                    );
                    border:1px solid rgba(0,0,0,0.25);
                "></div>
                <div style="
                    display:flex;
                    justify-content:space-between;
                    font-size:0.85rem;
                    margin-top:0.2rem;
                ">
                    <span>{scale_min:.2f}</span>
                    <span><b>{selected_metric}</b></span>
                    <span>{scale_max:.2f}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    values_array = np.asarray(values, dtype=float)
    finite = values_array[np.isfinite(values_array)]
    if finite.size:
        stat_cols = st.columns(4)
        stat_cols[0].metric("Minimum", f"{np.min(finite):.2f}")
        stat_cols[1].metric("Median", f"{np.median(finite):.2f}")
        stat_cols[2].metric("Mittelwert", f"{np.mean(finite):.2f}")
        stat_cols[3].metric("Maximum", f"{np.max(finite):.2f}")


def render_full_interactive_report(result: dict[str, Any]) -> None:
    items = result.get("interactive_report_items")
    if not isinstance(items, list) or not items:
        st.info("Für diesen Lauf wurden keine vollständigen Reportdaten bereitgestellt.")
        return

    chart_count = sum(1 for item in items if item.get("kind") == "chart")
    table_count = sum(1 for item in items if item.get("kind") == "table")
    st.caption(
        f"{chart_count} interaktive Diagramme und "
        f"{table_count} Tabellen aus dem PDF-Report."
    )

    st.markdown("### GPS-Trackkarte")
    render_colored_track_map(result)
    st.divider()

    for index, item in enumerate(items):
        title = item.get("title") or f"Auswertung {index + 1}"
        kind = item.get("kind")

        st.markdown(f"### {title}")

        if kind == "chart":
            render_serialized_report_chart(item)
        elif kind == "table":
            render_serialized_report_table(item)
        else:
            st.info(item.get("text", "Keine Darstellung verfügbar."))

        if index < len(items) - 1:
            st.divider()


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



BENCHMARK_REFERENCE_PATH = Path(__file__).parent / "data" / "Benchmark_Reference_API.json"

BENCHMARK_TOLERANCES = {
    "duration_s": 0.5,
    "distance_km": 0.01,
    "average_speed_kmh": 0.01,
    "average_power_w": 0.1,
    "normalized_power_w": 0.1,
    "elevation_gain_m": 0.5,
}


def parse_hhmmss(value: str) -> float:
    hours, minutes, seconds = [float(part) for part in value.split(":")]
    return hours * 3600 + minutes * 60 + seconds


def load_benchmark_reference() -> dict[str, Any] | None:
    try:
        return json.loads(BENCHMARK_REFERENCE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def find_profile_time(result: dict[str, Any], label: str) -> float | None:
    steps = result.get("profile_steps")
    if not isinstance(steps, list):
        return None
    for step in steps:
        if step.get("Abschnitt") == label:
            try:
                return float(step.get("Zeit [s]"))
            except (TypeError, ValueError):
                return None
    return None


def render_benchmark_comparison(result: dict[str, Any] | None) -> None:
    st.subheader("Benchmark: Aktuell vs. Referenz")
    reference = load_benchmark_reference()
    if reference is None:
        st.warning("Benchmark_Reference_API.json konnte nicht geladen werden.")
        return
    if not result:
        st.info("Nach einer Berechnung erscheint hier der automatische Referenzvergleich.")
        return

    ref = reference.get("results", {})
    definitions = [
        ("Radzeit", "duration_s", parse_hhmmss(str(ref.get("ride_time"))), "s", lambda v: format_duration(v)),
        ("Distanz", "distance_km", ref.get("distance_km"), "km", lambda v: f"{v:.2f} km"),
        ("Ø Geschwindigkeit", "average_speed_kmh", ref.get("average_speed_kmh"), "km/h", lambda v: f"{v:.2f} km/h"),
        ("Average Power", "average_power_w", ref.get("average_power_w"), "W", lambda v: f"{v:.1f} W"),
        ("Normalized Power", "normalized_power_w", ref.get("normalized_power_w"), "W", lambda v: f"{v:.1f} W"),
        ("Höhenmeter", "elevation_gain_m", ref.get("elevation_gain_m"), "m", lambda v: f"{v:.2f} m"),
    ]

    rows = []
    all_ok = True
    for label, key, ref_value, unit, formatter in definitions:
        current = result.get(key)
        if current is None or ref_value is None:
            rows.append({
                "Kennzahl": label,
                "Referenz": "—" if ref_value is None else formatter(float(ref_value)),
                "Aktuell": "—",
                "Abweichung": "—",
                "Status": "⚪ nicht verfügbar",
            })
            all_ok = False
            continue

        current = float(current)
        ref_value = float(ref_value)
        delta = current - ref_value
        tolerance = BENCHMARK_TOLERANCES[key]
        ok = abs(delta) <= tolerance
        all_ok = all_ok and ok
        if key == "duration_s":
            delta_text = f"{delta:+.2f} s"
        else:
            delta_text = f"{delta:+.3f} {unit}"
        rows.append({
            "Kennzahl": label,
            "Referenz": formatter(ref_value),
            "Aktuell": formatter(current),
            "Abweichung": delta_text,
            "Status": "✅ innerhalb Toleranz" if ok else "❌ abweichend",
        })

    if all_ok:
        st.success("Alle verfügbaren Benchmarkwerte liegen innerhalb der festgelegten Toleranzen.")
    else:
        st.warning("Mindestens ein Benchmarkwert fehlt oder liegt außerhalb der Toleranz.")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    current_core = find_profile_time(result, "Bike-Power-Kalkulation Hauptlauf")
    perf_ref = reference.get("performance_reference", {})
    reference_core = perf_ref.get("bike_power_calculation_s_uncached")
    cache_info = result.get("weather_api_cache") or {}

    perf_rows = []
    if current_core is not None and reference_core is not None:
        delta = current_core - float(reference_core)
        percent = delta / float(reference_core) * 100 if float(reference_core) else 0.0
        perf_rows.append({
            "Kennzahl": "Bike-Power-Hauptlauf",
            "Referenz": f"{float(reference_core):.3f} s",
            "Aktuell": f"{current_core:.3f} s",
            "Änderung": f"{delta:+.3f} s ({percent:+.1f} %)",
        })
    perf_rows.extend([
        {"Kennzahl": "API-Cache Treffer", "Referenz": "—", "Aktuell": str(cache_info.get("hits", "—")), "Änderung": "—"},
        {"Kennzahl": "API-Cache Fehlschläge", "Referenz": "—", "Aktuell": str(cache_info.get("misses", "—")), "Änderung": "—"},
        {"Kennzahl": "API-Anfragen", "Referenz": "—", "Aktuell": str(cache_info.get("requests", "—")), "Änderung": "—"},
    ])
    st.markdown("**Performance und Wetter-Cache**")
    st.dataframe(pd.DataFrame(perf_rows), use_container_width=True, hide_index=True)

def render_developer_diagnostics(result: dict[str, Any] | None, profile: dict[str, float] | None) -> None:
    st.subheader("Entwicklerdiagnose")
    render_benchmark_comparison(result)
    st.divider()

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

    with st.expander(f"Changelog Version {APP_VERSION}"):
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



def _json_safe_value(value: Any, max_sequence_items: int = 20000) -> Any:
    """Converts calculation data to a GitHub-storable JSON representation."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): _json_safe_value(item, max_sequence_items)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        values = list(value)
        if len(values) > max_sequence_items:
            step = max(1, len(values) // max_sequence_items)
            values = values[::step]
        return [
            _json_safe_value(item, max_sequence_items)
            for item in values
        ]

    try:
        if isinstance(value, np.ndarray):
            values = value
            if value.size > max_sequence_items:
                step = max(1, value.size // max_sequence_items)
                values = value.reshape(-1)[::step]
            return values.tolist()
    except Exception:
        pass

    try:
        if hasattr(value, "item"):
            return value.item()
    except Exception:
        pass

    return str(value)


def build_calculation_result_snapshot(result: dict[str, Any]) -> dict[str, Any]:
    """Creates a reproducible result snapshot without transient local paths."""
    excluded_keys = {
        "pdf_path",
        "map_path",
    }
    snapshot = {
        key: _json_safe_value(value)
        for key, value in result.items()
        if key not in excluded_keys
    }
    snapshot["app_version"] = APP_VERSION
    snapshot["engine_version"] = ENGINE_VERSION
    snapshot["saved_at"] = datetime.now().isoformat(timespec="seconds")
    return snapshot


def infer_calculation_type(result: dict[str, Any], config: dict[str, Any]) -> str:
    route_path = str(config.get("GPX/FIT Datei", "")).lower()
    target_speed = result.get("calibration_target_speed_kmh")
    try:
        if route_path.endswith(".fit") and float(target_speed) > 0:
            return "fit_cda_calibration"
    except (TypeError, ValueError):
        pass
    if route_path.endswith(".fit"):
        return "fit_analysis"
    return "route_simulation"


def render_save_calculation_to_github(
    result: dict[str, Any],
    run_log: str,
    profile: dict[str, Any] | None,
) -> None:
    db = get_github_database()
    selected_event_id = st.session_state.get(
        "github_database_selected_event"
    )

    with st.expander("Aktuelle Berechnung im GitHub-Event speichern", expanded=False):
        if db is None:
            st.info("Die GitHub-Datenbank ist nicht konfiguriert.")
            return
        if not selected_event_id:
            st.info(
                "Bitte zuerst links unter GitHub-Datenbank ein Event auswählen."
            )
            return

        try:
            event = db.load_event(selected_event_id)
        except GitHubDatabaseError as exc:
            st.error(str(exc))
            return

        st.caption(f"Ziel-Event: {event.get('name', selected_event_id)}")

        default_name = (
            f"{result.get('title', 'Berechnung')} · "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        calculation_name = st.text_input(
            "Name der Berechnung",
            value=default_name,
            key="github_calculation_name",
        )

        include_pdf = st.checkbox(
            "Vorhandene PDF mitspeichern",
            value=True,
            key="github_calculation_include_pdf",
        )
        include_html = st.checkbox(
            "Vorhandene HTML-Karte mitspeichern",
            value=True,
            key="github_calculation_include_html",
        )

        if st.button(
            "Berechnung jetzt speichern",
            key="github_save_current_calculation",
            type="primary",
            use_container_width=True,
        ):
            pdf_content = None
            pdf_filename = None
            html_content = None
            html_filename = None
            weather_content = None
            weather_filename = None

            weather_snapshot = result.get("weather_snapshot")
            if weather_snapshot:
                weather_content = json.dumps(
                    weather_snapshot,
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8")
                weather_filename = "online_weather_snapshot.json"

            pdf_path_value = result.get("pdf_path")
            if include_pdf and pdf_path_value:
                pdf_path = Path(pdf_path_value)
                if pdf_path.exists():
                    pdf_content = pdf_path.read_bytes()
                    pdf_filename = pdf_path.name

            map_path_value = result.get("map_path")
            if include_html and map_path_value:
                map_path = Path(map_path_value)
                if map_path.exists():
                    html_content = map_path.read_bytes()
                    html_filename = map_path.name

            try:
                with st.spinner("Berechnung wird auf GitHub gespeichert …"):
                    metadata = db.save_calculation(
                        selected_event_id,
                        name=calculation_name,
                        calculation_type=infer_calculation_type(
                            result,
                            st.session_state.config,
                        ),
                        settings=_json_safe_value(
                            dict(st.session_state.config)
                        ),
                        result=build_calculation_result_snapshot(result),
                        profiler=_json_safe_value(profile or {}),
                        run_log=run_log or result.get("run_log", ""),
                        pdf_content=pdf_content,
                        pdf_filename=pdf_filename,
                        html_content=html_content,
                        html_filename=html_filename,
                        weather_content=weather_content,
                        weather_filename=weather_filename,
                    )
                st.success(
                    f"Berechnung „{metadata['name']}“ wurde gespeichert."
                )
                st.caption(f"Berechnungs-ID: {metadata['id']}")
            except (GitHubDatabaseError, TypeError, ValueError) as exc:
                st.error(f"Berechnung konnte nicht gespeichert werden: {exc}")


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

    power_cols = st.columns(2)
    average_power = result.get("calibration_ap")
    if average_power is None:
        average_power = result.get("average_power_w")

    normalized_power = result.get("calibration_np")
    if normalized_power is None:
        normalized_power = result.get("normalized_power_w")

    power_cols[0].metric(
        "Average Power",
        "—" if average_power is None else f"{float(average_power):.2f} W",
    )
    power_cols[1].metric(
        "Normalized Power",
        "—" if normalized_power is None else f"{float(normalized_power):.2f} W",
    )

    render_save_calculation_to_github(result, run_log, profile)

    weather_snapshot = result.get("weather_snapshot")
    if weather_snapshot:
        st.download_button(
            "Online-Wetterdaten als JSON herunterladen",
            data=json.dumps(weather_snapshot, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=(
                re.sub(r"[^A-Za-z0-9._-]+", "_", str(result.get("title", "weather"))).strip("_")
                + "_online_weather.json"
            ),
            mime="application/json",
            use_container_width=True,
        )
        st.caption(
            f"Wetterquelle: {result.get('weather_source_mode', 'online_api')} · "
            f"gespeicherte API-Datensätze: {len(weather_snapshot.get('requests', []))}"
        )

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

    st.subheader("Vollständige interaktive Auswertung")
    render_interactive_charts(result)

    if pdf_path and pdf_path.exists():
        with st.expander("PDF-Vorschau anzeigen", expanded=False):
            pdf_viewer(pdf_path)

    if map_path and map_path.exists():
        with st.expander("HTML-Karte anzeigen", expanded=False):
            html_map_viewer(map_path)

    with st.expander("Berechnungslog anzeigen", expanded=False):
        effective_log = run_log
        if not effective_log and isinstance(result, dict):
            effective_log = result.get("run_log", "")

        if effective_log:
            st.code(effective_log)
        else:
            st.info("Kein Berechnungslog vorhanden.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def render_kernel_profile(result: dict) -> None:
    kernel = result.get('kernel_profile')
    if not isinstance(kernel, dict):
        return

    sections = kernel.get('sections', {})
    calls = kernel.get('calls', {})
    meta = kernel.get('meta', {})
    runs = kernel.get('runs', [])
    calc_v = kernel.get('calc_v', {})

    st.subheader('Deep Profiler')
    cols = st.columns(4)
    cols[0].metric('Vollständige Rechenläufe', len(runs))
    cols[1].metric('Punkte je Lauf', meta.get('points_per_run', '—'))
    total = sections.get('bike_power_main_calc gesamt')
    cols[2].metric('Hauptläufe kumuliert', '—' if total is None else f'{total:.2f} s')
    cv_total = calc_v.get('sections', {}).get('calc_v gesamt intern')
    cols[3].metric('calc_v kumuliert', '—' if cv_total is None else f'{cv_total:.2f} s')

    if runs:
        run_rows=[]
        for run in runs:
            run_rows.append({
                'Lauf': run.get('run'),
                'Typ': run.get('type'),
                'Zeit [s]': run.get('time_s'),
                'Punkte': run.get('points'),
                'Glättung n': run.get('n_smoothing'),
                'fNP': run.get('f_np'),
                'NP [W]': run.get('np_w'),
                'AP [W]': run.get('ap_w'),
                'Speed [km/h]': run.get('speed_kmh'),
                'CdA flach': run.get('cda_flat'),
            })
        df_runs=pd.DataFrame(run_rows)
        st.markdown('#### Einzelne Hauptläufe / Konvergenz')
        st.dataframe(df_runs, use_container_width=True, hide_index=True)
        st.download_button('Hauptläufe als CSV herunterladen', df_runs.to_csv(index=False).encode('utf-8'), 'profiling_runs.csv', 'text/csv')

    if sections:
        rows=[]
        for name, seconds in sections.items():
            count=int(calls.get(name,0))
            rows.append({'Abschnitt':name,'Zeit [s]':float(seconds),'Aufrufe':count,'ms/Aufruf':(float(seconds)*1000/count) if count else None})
        df=pd.DataFrame(rows).sort_values('Zeit [s]',ascending=False)
        st.markdown('#### Kumuliertes Profil aller Hauptläufe')
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.download_button('Kumuliertes Profil als CSV herunterladen',df.to_csv(index=False).encode('utf-8'),'profiling_kernel.csv','text/csv')
        top=df[df['Abschnitt']!='bike_power_main_calc gesamt'].head(5)
        if not top.empty: st.bar_chart(top.set_index('Abschnitt')['Zeit [s]'])

    cv_sections=calc_v.get('sections',{})
    cv_calls=calc_v.get('calls',{})
    branches=calc_v.get('branches',{})
    if cv_sections:
        cv_rows=[]
        for name,seconds in cv_sections.items():
            count=int(cv_calls.get(name,0))
            cv_rows.append({'calc_v Abschnitt':name,'Zeit [s]':float(seconds),'Aufrufe':count,'ms/Aufruf':(float(seconds)*1000/count) if count else None})
        df_cv=pd.DataFrame(cv_rows).sort_values('Zeit [s]',ascending=False)
        st.markdown('#### Deep Profiling von calc_v()')
        st.dataframe(df_cv,use_container_width=True,hide_index=True)
        b1,b2=st.columns(2)
        b1.metric('Kubischer Zweig Δ ≥ 0',int(branches.get('delta_ge_0',0)))
        b2.metric('Kubischer Zweig Δ < 0',int(branches.get('delta_lt_0',0)))
        st.caption('calc_v löst die Geschwindigkeit analytisch über eine kubische Gleichung; es gibt keinen iterativen Solver.')
        st.download_button('calc_v Profil als CSV herunterladen',df_cv.to_csv(index=False).encode('utf-8'),'profiling_calc_v.csv','text/csv')


def render_fit_cache_debug(result: dict) -> None:
    st.subheader("FIT-Cache-Debug")

    hit = result.get("fit_cache_hit")
    key = result.get("fit_cache_key")
    path = result.get("fit_cache_path")
    exists_before = result.get("fit_cache_exists_before")
    read_s = result.get("fit_cache_read_s")
    write_s = result.get("fit_cache_write_s")
    parse_s = result.get("fit_parse_s")

    cols = st.columns(4)
    cols[0].metric("Status", "Treffer" if hit else "Miss")
    cols[1].metric("Vorher vorhanden", "Ja" if exists_before else "Nein")
    cols[2].metric("Lesezeit", "—" if read_s is None else f"{read_s:.3f} s")
    cols[3].metric("Parsingzeit", "—" if parse_s is None else f"{parse_s:.3f} s")

    rows = [
        {"Feld": "Cache-Key", "Wert": key or "—"},
        {"Feld": "Cache-Pfad", "Wert": path or "—"},
        {"Feld": "Vorher vorhanden", "Wert": exists_before},
        {"Feld": "Cache-Treffer", "Wert": hit},
        {"Feld": "Lesezeit [s]", "Wert": read_s},
        {"Feld": "Parsingzeit [s]", "Wert": parse_s},
        {"Feld": "Schreibzeit [s]", "Wert": write_s},
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)



def should_show_cda_calibration(result: dict, config: dict) -> bool:
    """CdA-Kalibrierung nur für FIT-Dateien mit positivem Speed_Soll anzeigen."""
    route_file = str(config.get("GPX/FIT Datei", "")).strip().lower()
    if not route_file.endswith(".fit"):
        return False

    target_speed = result.get("calibration_target_speed_kmh")
    if target_speed is None:
        # Fallback: Speed_Soll steckt als zweiter Wert im CdA-Feld.
        raw_cda = str(config.get("cdA im Flachen [m^2]", ""))
        try:
            numbers = [float(value.replace(",", ".")) for value in re.findall(r"-?\d+(?:[\.,]\d+)?", raw_cda)]
            target_speed = numbers[1] if len(numbers) > 1 else -1
        except Exception:
            target_speed = -1

    try:
        return float(target_speed) > 0
    except (TypeError, ValueError):
        return False


def render_cda_calibration_summary(result: dict, config: dict) -> None:
    """Kompakte Ergebnisübersicht für FIT-basierte CdA-Kalibrierungen."""
    cda = result.get("calibration_cda")
    cda_start = result.get("calibration_cda_start")
    ap = result.get("calibration_ap")
    np_value = result.get("calibration_np")
    speed = result.get("calibration_speed_kmh")
    if speed is None:
        speed = result.get("average_speed_kmh")

    target_speed = result.get("calibration_target_speed_kmh")
    target_np = result.get("calibration_target_np")
    target_ap = result.get("calibration_target_ap")
    f_np = result.get("calibration_f_np")
    moving_average = result.get("calibration_moving_average")
    runs = result.get("calibration_runs")

    if f_np is None:
        run_rows = result.get("run_profile_rows")
        if isinstance(run_rows, list) and run_rows:
            last_row = run_rows[-1]
            if isinstance(last_row, dict):
                for key in ("fNP", "f_NP", "f_NP_Soll", "f_NP_Soll_fit"):
                    if last_row.get(key) is not None:
                        f_np = last_row.get(key)
                        break

    if runs is None:
        run_rows = result.get("run_profile_rows")
        if isinstance(run_rows, list):
            runs = len(run_rows)
        else:
            kernel = result.get("kernel_profile", {})
            calls = kernel.get("calls", {}) if isinstance(kernel, dict) else {}
            runs = calls.get("bike_power_main_calc gesamt")

    try:
        if target_np is None:
            target_np = float(config.get("Normalized Power Sollwert [W]"))
    except Exception:
        pass
    try:
        if target_ap is None:
            target_ap = float(config.get("Leistung bei 0% Steigung [W]"))
    except Exception:
        pass

    st.subheader("CdA-Kalibrierung")
    cols = st.columns(6)
    cols[0].metric("CdA Startwert", "—" if cda_start is None else f"{float(cda_start):.5f}")
    cols[1].metric("CdA berechnet", "—" if cda is None else f"{float(cda):.5f}")
    cols[2].metric("Average Power", "—" if ap is None else f"{float(ap):.2f} W")
    cols[3].metric("Normalized Power", "—" if np_value is None else f"{float(np_value):.2f} W")
    cols[4].metric("Ø Geschwindigkeit", "—" if speed is None else f"{float(speed):.3f} km/h")
    cols[5].metric("Hauptläufe", "—" if runs is None else int(runs))

    def delta(current, target):
        if current is None or target is None:
            return None
        return float(current) - float(target)

    speed_delta = delta(speed, target_speed)
    ap_delta = delta(ap, target_ap)
    np_delta = delta(np_value, target_np)
    rows = [
        {"Größe":"Durchschnittsgeschwindigkeit","Soll":target_speed,"Ist":speed,"Abweichung":speed_delta,"Toleranz":0.01,"Status":"✅" if speed_delta is not None and abs(speed_delta)<=0.01 else "⚠️"},
        {"Größe":"Average Power","Soll":target_ap,"Ist":ap,"Abweichung":ap_delta,"Toleranz":0.1,"Status":"✅" if ap_delta is not None and abs(ap_delta)<=0.1 else "⚠️"},
        {"Größe":"Normalized Power","Soll":target_np,"Ist":np_value,"Abweichung":np_delta,"Toleranz":0.1,"Status":"✅" if np_delta is not None and abs(np_delta)<=0.1 else "⚠️"},
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    dcols = st.columns(3)
    dcols[0].metric("fNP", "—" if f_np is None else f"{float(f_np):.6f}")
    dcols[1].metric("Moving Average n", "—" if moving_average is None else int(moving_average))
    dcols[2].metric("FIT-Cache", "Treffer" if result.get("fit_cache_hit") else "Miss")
    if all(row["Status"]=="✅" for row in rows):
        st.success("CdA-Kalibrierung erfolgreich: Geschwindigkeit, AP und NP liegen innerhalb der Toleranzen.")
    else:
        st.warning("Kalibrierung abgeschlossen, aber mindestens ein Zielwert liegt außerhalb der Toleranz.")


def get_github_database_config() -> GitHubDatabaseConfig | None:
    try:
        section = st.secrets.get("github_database", {})
    except Exception:
        return None
    token = str(section.get("token", "")).strip()
    owner = str(section.get("owner", "")).strip()
    repo = str(section.get("repo", "")).strip()
    if not token or not owner or not repo:
        return None
    return GitHubDatabaseConfig(token=token, owner=owner, repo=repo,
        branch=str(section.get("branch", "main")).strip() or "main",
        root_path=str(section.get("root_path", "Database")).strip() or "Database")


def get_github_database() -> GitHubDatabase | None:
    config = get_github_database_config()
    return None if config is None else GitHubDatabase(config)



def render_github_database_sidebar() -> None:
    db = get_github_database()

    st.divider()
    st.subheader("☁️ GitHub-Datenbank")

    if db is None:
        st.warning("GitHub-Datenbank ist noch nicht konfiguriert.")
        st.code(
            """[github_database]
token = "github_pat_..."
owner = "DEIN_GITHUB_NAME"
repo = "bike-power-database"
branch = "main"
root_path = "Database"
""",
            language="toml",
        )
        return

    config = db.config
    st.caption(f"{config.owner}/{config.repo} · Branch {config.branch}")

    connection_col, init_col = st.columns(2)
    if connection_col.button("Verbindung testen", key="github_db_test", use_container_width=True):
        try:
            info = db.test_connection()
            st.success(
                f"Verbunden mit {info.get('full_name')} · "
                f"{'Privat' if info.get('private') else 'Öffentlich'}"
            )
        except GitHubDatabaseError as exc:
            st.error(str(exc))

    if init_col.button("Initialisieren", key="github_db_initialize", use_container_width=True):
        try:
            db.initialize()
            st.success("Database/index.json ist vorhanden.")
            st.rerun()
        except GitHubDatabaseError as exc:
            st.error(str(exc))

    try:
        events = db.list_events()
    except GitHubDatabaseError as exc:
        st.error(str(exc))
        return

    tabs = st.tabs(["Events", "Neu", "Bearbeiten", "Dateien", "Berechnungen"])

    with tabs[0]:
        search = st.text_input("Suchen", key="github_database_search").strip().lower()
        filtered = []
        for event in events:
            searchable = " ".join(
                [
                    str(event.get("name", "")),
                    str(event.get("date", "")),
                    str(event.get("location", "")),
                    str(event.get("sport", "")),
                    " ".join(event.get("tags", [])),
                ]
            ).lower()
            if not search or search in searchable:
                filtered.append(event)

        if not filtered:
            st.info("Keine passenden Events vorhanden.")
        else:
            labels = {}
            for event in filtered:
                base_label = (
                    f"{event.get('name', event.get('id'))} · "
                    f"{event.get('date') or 'ohne Datum'}"
                )
                label = base_label
                if label in labels:
                    label = f"{base_label} · {event.get('id')}"
                labels[label] = event.get("id")

            selected_label = st.selectbox(
                "Event auswählen",
                list(labels.keys()),
                key="github_database_selected_label",
            )
            selected_id = labels[selected_label]
            st.session_state.github_database_selected_event = selected_id

            try:
                selected_event = db.load_event(selected_id)
                st.caption(
                    f"{selected_event.get('location') or '—'} · "
                    f"{selected_event.get('sport') or '—'} · "
                    f"{', '.join(selected_event.get('tags', [])) or 'keine Tags'}"
                )

                try:
                    saved_calculations = db.list_calculations(selected_id)
                    if saved_calculations:
                        st.caption(
                            f"Gespeicherte Berechnungen: {len(saved_calculations)}"
                        )
                except GitHubDatabaseError:
                    pass
            except GitHubDatabaseError as exc:
                st.error(str(exc))

            if st.button(
                "Metadaten anzeigen",
                key="github_db_show_event",
                use_container_width=True,
            ):
                try:
                    st.json(db.load_event(selected_id))
                except GitHubDatabaseError as exc:
                    st.error(str(exc))

    with tabs[1]:
        with st.form("github_database_new_event_form"):
            name = st.text_input("Eventname")
            event_date = st.date_input("Eventdatum", value=None)
            location = st.text_input("Ort")
            sport = st.selectbox(
                "Eventtyp",
                ["Triathlon", "Radrennen", "Training", "Strecke", "Sonstiges"],
            )
            tags_text = st.text_input("Tags, durch Kommas getrennt")
            notes = st.text_area("Notizen")
            st.caption(
                "Das Event wird zunächst nur mit event.json angelegt. "
                "Einstellungen können anschließend unter frei wählbarem Namen gespeichert werden."
            )
            submitted = st.form_submit_button("Auf GitHub anlegen")

        if submitted:
            if not name.strip():
                st.error("Bitte einen Eventnamen eingeben.")
            else:
                try:
                    duplicates = db.find_events_by_name(name)
                    if duplicates:
                        st.warning(
                            f"Es existieren bereits {len(duplicates)} Event(s) "
                            f"mit dem Namen „{name}“. Das neue Event wird trotzdem "
                            "mit eigener UUID angelegt."
                        )
                    event = db.create_event(
                        name=name,
                        event_date="" if event_date is None else event_date.isoformat(),
                        location=location,
                        sport=sport,
                        tags=[tag.strip() for tag in tags_text.split(",") if tag.strip()],
                        notes=notes,
                        settings=None,
                    )
                    st.session_state.github_database_selected_event = event["id"]
                    st.success(f"Event „{event['name']}“ wurde angelegt.")
                    st.rerun()
                except GitHubDatabaseError as exc:
                    st.error(str(exc))

    with tabs[2]:
        selected_id = st.session_state.get("github_database_selected_event")
        if not selected_id:
            st.info("Zuerst im Tab „Events“ ein Event auswählen.")
        else:
            try:
                event = db.load_event(selected_id)
            except GitHubDatabaseError as exc:
                st.error(str(exc))
                event = None

            if event:
                with st.form(f"github_edit_event_{selected_id}"):
                    name = st.text_input("Name", value=event.get("name", ""))
                    current_date = None
                    if event.get("date"):
                        try:
                            current_date = datetime.fromisoformat(event["date"]).date()
                        except Exception:
                            current_date = None
                    event_date = st.date_input("Datum", value=current_date)
                    location = st.text_input("Ort", value=event.get("location", ""))
                    sports = ["Triathlon", "Radrennen", "Training", "Strecke", "Sonstiges"]
                    current_sport = event.get("sport", "Triathlon")
                    sport_index = sports.index(current_sport) if current_sport in sports else 0
                    sport = st.selectbox("Typ", sports, index=sport_index)
                    tags_text = st.text_input(
                        "Tags",
                        value=", ".join(event.get("tags", [])),
                    )
                    notes = st.text_area("Notizen", value=event.get("notes", ""))
                    update_settings = st.checkbox(
                        "Aktuelle Einstellungen als settings.json übernehmen",
                        value=False,
                    )
                    save_changes = st.form_submit_button("Änderungen speichern")

                if save_changes:
                    try:
                        db.update_event(
                            selected_id,
                            name=name,
                            event_date="" if event_date is None else event_date.isoformat(),
                            location=location,
                            sport=sport,
                            tags=[tag.strip() for tag in tags_text.split(",") if tag.strip()],
                            notes=notes,
                            settings=dict(st.session_state.config) if update_settings else None,
                        )
                        st.success("Event wurde aktualisiert.")
                        st.rerun()
                    except GitHubDatabaseError as exc:
                        st.error(str(exc))

                st.markdown("**Event duplizieren**")
                duplicate_name = st.text_input(
                    "Name der Kopie",
                    value=f"{event.get('name', 'Event')} (Kopie)",
                    key=f"github_duplicate_name_{selected_id}",
                )
                if st.button(
                    "Event duplizieren",
                    key=f"github_duplicate_{selected_id}",
                    use_container_width=True,
                ):
                    try:
                        copied = db.duplicate_event(selected_id, duplicate_name)
                        st.session_state.github_database_selected_event = copied["id"]
                        st.success(f"Event wurde als „{copied['name']}“ dupliziert.")
                        st.rerun()
                    except GitHubDatabaseError as exc:
                        st.error(str(exc))

                st.markdown("**Event löschen**")
                confirm_delete = st.checkbox(
                    f"Ich möchte „{event.get('name')}“ endgültig löschen.",
                    key=f"github_confirm_delete_{selected_id}",
                )
                if st.button(
                    "Event endgültig löschen",
                    key=f"github_delete_{selected_id}",
                    type="secondary",
                    disabled=not confirm_delete,
                    use_container_width=True,
                ):
                    try:
                        db.delete_event(selected_id)
                        st.session_state.github_database_selected_event = None
                        st.success("Event wurde gelöscht.")
                        st.rerun()
                    except GitHubDatabaseError as exc:
                        st.error(str(exc))

    with tabs[3]:
        selected_id = st.session_state.get("github_database_selected_event")
        if not selected_id:
            st.info("Zuerst im Tab „Events“ ein Event auswählen.")
        else:
            try:
                files = db.list_event_files(selected_id)
            except GitHubDatabaseError as exc:
                st.error(str(exc))
                files = []

            st.markdown("**Aktuelle Einstellungen speichern**")
            settings_filename = st.text_input(
                "Dateiname",
                value="settings.json",
                key=f"github_settings_filename_{selected_id}",
                help="Die Endung .json wird bei Bedarf automatisch ergänzt.",
            )
            if st.button(
                "Aktuelle Einstellungen im Event speichern",
                key=f"github_save_current_settings_{selected_id}",
                use_container_width=True,
            ):
                try:
                    saved_name = db.save_named_settings(
                        selected_id,
                        settings_filename,
                        _json_safe_value(dict(st.session_state.config)),
                    )
                    st.success(f"{saved_name} wurde gespeichert.")
                    st.rerun()
                except (GitHubDatabaseError, ValueError) as exc:
                    st.error(str(exc))

            st.divider()

            uploads = st.file_uploader(
                "JSON-, GPX-, FIT- oder CSV-Dateien hochladen",
                type=["json", "gpx", "fit", "csv"],
                accept_multiple_files=True,
                key=f"github_event_upload_{selected_id}",
            )
            if uploads and st.button(
                "Dateien auf GitHub speichern",
                key=f"github_save_files_{selected_id}",
                use_container_width=True,
            ):
                try:
                    upload_status = st.empty()
                    for upload_index, uploaded in enumerate(uploads, start=1):
                        content = uploaded.getvalue()
                        size_mb = len(content) / (1024 * 1024)
                        suffix = Path(uploaded.name).suffix.lower()
                        upload_mode = (
                            "Git Commit/Push"
                            if suffix in {".fit", ".gpx"} or len(content) > 1024 * 1024
                            else "REST-Upload"
                        )
                        upload_status.info(
                            f"Lade {uploaded.name} hoch "
                            f"({size_mb:.2f} MB, {upload_mode}, "
                            f"Datei {upload_index}/{len(uploads)}) …"
                        )
                        db.save_event_file(
                            selected_id,
                            uploaded.name,
                            content,
                            f"Save {uploaded.name} for event {selected_id}",
                        )
                    upload_status.empty()
                    st.success(f"{len(uploads)} Datei(en) gespeichert.")
                    st.rerun()
                except GitHubDatabaseError as exc:
                    st.error(str(exc))
                    st.caption(
                        "Bitte die angezeigte Stufe und die GitHub Request-ID "
                        "für die Fehleranalyse kopieren."
                    )

            if not files:
                st.info("Noch keine Dateien im Event vorhanden.")
            else:
                file_df = pd.DataFrame(files)
                file_df["size_kb"] = file_df["size"].fillna(0) / 1024
                if "storage" not in file_df.columns:
                    file_df["storage"] = "direct"
                st.dataframe(
                    file_df[["name", "size_kb", "storage"]].rename(
                        columns={
                            "name": "Datei",
                            "size_kb": "Größe [KB]",
                            "storage": "Speicherung",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

                selected_file = st.selectbox(
                    "Datei auswählen",
                    [item["name"] for item in files],
                    key=f"github_event_file_select_{selected_id}",
                )
                suffix = Path(selected_file).suffix.lower()
                content = None
                try:
                    content = db.load_event_file(selected_id, selected_file)
                except GitHubDatabaseError as exc:
                    st.error(str(exc))

                if content is not None:
                    st.download_button(
                        "Datei herunterladen",
                        data=content,
                        file_name=selected_file,
                        mime="application/octet-stream",
                        use_container_width=True,
                    )

                    action_cols = st.columns(2)
                    if suffix == ".json":
                        if action_cols[0].button(
                            "Als Einstellungen laden",
                            key=f"github_load_json_file_{selected_id}",
                            use_container_width=True,
                        ):
                            try:
                                loaded = json.loads(content.decode("utf-8"))
                                loaded_config = normalize_loaded_config(loaded)
                                st.session_state.config = loaded_config
                                sync_widgets_from_config(loaded_config)
                                st.success("JSON wurde als Einstellungen geladen.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"JSON konnte nicht geladen werden: {exc}")
                    elif suffix in {".gpx", ".fit", ".csv"}:
                        if action_cols[0].button(
                            "In App laden",
                            key=f"github_load_data_file_{selected_id}",
                            use_container_width=True,
                        ):
                            runtime_dir = Path("runtime_uploads")
                            runtime_dir.mkdir(parents=True, exist_ok=True)
                            target = runtime_dir / Path(selected_file).name
                            target.write_bytes(content)

                            config = dict(st.session_state.config)
                            if suffix in {".gpx", ".fit"}:
                                config["GPX/FIT Datei"] = str(target)
                            elif suffix == ".csv":
                                config["Wetterdatei Advanced Weather"] = str(target)

                            st.session_state.config = normalize_loaded_config(config)
                            sync_widgets_from_config(st.session_state.config)
                            st.success(f"{selected_file} wurde in die App geladen.")
                            st.rerun()

                    if action_cols[1].button(
                        "Datei löschen",
                        key=f"github_delete_file_{selected_id}",
                        use_container_width=True,
                    ):
                        try:
                            db.delete_event_file(
                                selected_id,
                                selected_file,
                            )
                            st.success(f"{selected_file} wurde gelöscht.")
                            st.rerun()
                        except GitHubDatabaseError as exc:
                            st.error(str(exc))

    with tabs[4]:
        selected_id = st.session_state.get("github_database_selected_event")
        if not selected_id:
            st.info("Zuerst im Tab „Events“ ein Event auswählen.")
        else:
            try:
                calculations = db.list_calculations(selected_id)
            except GitHubDatabaseError as exc:
                st.error(str(exc))
                calculations = []

            if not calculations:
                st.info("Für dieses Event sind noch keine Berechnungen gespeichert.")
            else:
                calculation_labels = {
                    (
                        f"{item.get('name', item.get('id'))} · "
                        f"{str(item.get('created_at', ''))[:16].replace('T', ' ')}"
                    ): item.get("id")
                    for item in calculations
                }
                selected_calc_label = st.selectbox(
                    "Berechnung auswählen",
                    list(calculation_labels.keys()),
                    key=f"github_calculation_select_{selected_id}",
                )
                calculation_id = calculation_labels[selected_calc_label]
                metadata = next(
                    item for item in calculations
                    if item.get("id") == calculation_id
                )

                summary = metadata.get("summary", {})
                summary_cols = st.columns(2)
                summary_cols[0].metric(
                    "Zeit",
                    format_duration(summary.get("duration_s")),
                )
                summary_cols[1].metric(
                    "Ø Geschwindigkeit",
                    "—" if summary.get("average_speed_kmh") is None
                    else f"{float(summary['average_speed_kmh']):.2f} km/h",
                )
                summary_cols[0].metric(
                    "Average Power",
                    "—" if summary.get("average_power_w") is None
                    else f"{float(summary['average_power_w']):.2f} W",
                )
                summary_cols[1].metric(
                    "Normalized Power",
                    "—" if summary.get("normalized_power_w") is None
                    else f"{float(summary['normalized_power_w']):.2f} W",
                )
                if summary.get("cda") is not None:
                    st.metric("CdA", f"{float(summary['cda']):.5f}")

                action_cols = st.columns(3)

                if action_cols[0].button(
                    "Ergebnisse laden",
                    key=f"github_load_results_{calculation_id}",
                    use_container_width=True,
                ):
                    try:
                        loaded_result = db.load_calculation_json(
                            selected_id,
                            calculation_id,
                            "result.json",
                        )
                        loaded_profile = db.load_calculation_json(
                            selected_id,
                            calculation_id,
                            "profiler.json",
                        )
                        loaded_log = db.load_calculation_text(
                            selected_id,
                            calculation_id,
                            "run_log.txt",
                        )
                        st.session_state.result = loaded_result
                        st.session_state.profile = loaded_profile
                        st.session_state.run_log = loaded_log
                        st.success("Ergebnisse wurden geladen.")
                        st.rerun()
                    except (GitHubDatabaseError, json.JSONDecodeError) as exc:
                        st.error(f"Ergebnisse konnten nicht geladen werden: {exc}")

                if action_cols[1].button(
                    "Einstellungen laden",
                    key=f"github_load_calc_settings_{calculation_id}",
                    use_container_width=True,
                ):
                    try:
                        settings = db.load_calculation_json(
                            selected_id,
                            calculation_id,
                            "settings_snapshot.json",
                        )
                        loaded_config = normalize_loaded_config(settings)
                        st.session_state.config = loaded_config
                        sync_widgets_from_config(loaded_config)
                        st.success("Einstellungen wurden geladen.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Einstellungen konnten nicht geladen werden: {exc}")

                if action_cols[2].button(
                    "Alles laden",
                    key=f"github_load_all_{calculation_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    try:
                        settings = db.load_calculation_json(
                            selected_id,
                            calculation_id,
                            "settings_snapshot.json",
                        )
                        loaded_result = db.load_calculation_json(
                            selected_id,
                            calculation_id,
                            "result.json",
                        )
                        loaded_profile = db.load_calculation_json(
                            selected_id,
                            calculation_id,
                            "profiler.json",
                        )
                        loaded_log = db.load_calculation_text(
                            selected_id,
                            calculation_id,
                            "run_log.txt",
                        )

                        runtime_dir = (
                            Path(tempfile.gettempdir())
                            / "bike_power_calculator_saved_calculations"
                            / calculation_id
                        )
                        runtime_dir.mkdir(parents=True, exist_ok=True)

                        for filename in metadata.get("files", []):
                            suffix = Path(filename).suffix.lower()
                            if suffix not in {".pdf", ".html", ".htm", ".json"}:
                                continue
                            try:
                                content = db.load_calculation_binary(
                                    selected_id,
                                    calculation_id,
                                    filename,
                                )
                            except GitHubDatabaseError:
                                continue
                            target = runtime_dir / Path(filename).name
                            target.write_bytes(content)
                            if suffix == ".pdf":
                                loaded_result["pdf_path"] = str(target)
                            elif suffix in {".html", ".htm"}:
                                loaded_result["map_path"] = str(target)
                            elif filename == metadata.get("weather_file") or "weather_snapshot" in filename:
                                loaded_result["weather_snapshot_path"] = str(target)
                                settings["Wetterdatei Advanced Weather"] = str(target)

                        loaded_config = normalize_loaded_config(settings)
                        st.session_state.config = loaded_config
                        sync_widgets_from_config(loaded_config)
                        st.session_state.result = loaded_result
                        st.session_state.profile = loaded_profile
                        st.session_state.run_log = loaded_log
                        st.success("Berechnung wurde vollständig geladen.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Berechnung konnte nicht geladen werden: {exc}")

                with st.expander("Metadaten anzeigen", expanded=False):
                    st.json(metadata)

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
        render_github_database_sidebar()

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
        weather_file = st.file_uploader(
            "Wetterdatei Advanced Weather",
            type=["csv", "json"],
            help=(
                "CSV verwendet das vereinfachte Wettermodell. Ein JSON-Snapshot "
                "verwendet vollständig gespeicherte Open-Meteo-Daten ohne API-Aufruf."
            ),
        )
        weather_path = save_uploaded_file(weather_file)
        if weather_path:
            config["Wetterdatei Advanced Weather"] = weather_path
            if Path(weather_path).suffix.lower() == ".json":
                st.success(f"Online-Wetter-Snapshot geladen: {weather_file.name}")
            else:
                st.success(f"Wetter-CSV geladen: {weather_file.name}")

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

    weather_mode = str(st.session_state.config.get("Verwendung Advanced Weather", ""))
    if weather_mode.startswith("True,True"):
        st.session_state.refresh_weather_cache = st.checkbox(
            "Online-Wetter neu laden",
            value=False,
            help=(
                "Löscht vor dieser Berechnung den lokalen Open-Meteo-Cache. "
                "Ohne Haken werden identische Abfragen bis zu 30 Tage wiederverwendet."
            ),
        )
    else:
        st.session_state.refresh_weather_cache = False

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

                    with contextlib.redirect_stdout(log_buffer), contextlib.redirect_stderr(log_buffer):
                        progress.progress(25, text="Strecke, Wetter, PDF und Karte werden berechnet …")
                        t_calc_start = time.perf_counter()
                        if st.session_state.refresh_weather_cache:
                            bpc.clear_weather_api_cache()
                        result = call_bike_power_calc(
                            run_config,
                            st.session_state.generate_pdf,
                            st.session_state.generate_html_map,
                        )
                        profile["calculation_s"] = time.perf_counter() - t_calc_start

                    t_post_start = time.perf_counter()
                    progress.progress(100, text="Berechnung abgeschlossen.")
                    captured_log = log_buffer.getvalue()
                    if not captured_log.strip():
                        captured_log = "Die Berechnung hat keine Textausgaben erzeugt."

                    if isinstance(result, dict):
                        result["run_log"] = captured_log
                        weather_snapshot = result.get("weather_snapshot")
                        if weather_snapshot:
                            weather_dir = Path(tempfile.gettempdir()) / "bike_power_weather_snapshots"
                            weather_dir.mkdir(parents=True, exist_ok=True)
                            safe_title = re.sub(r"[^A-Za-z0-9._-]+", "_", str(result.get("title", "weather"))).strip("_") or "weather"
                            weather_path = weather_dir / f"{safe_title}_online_weather.json"
                            weather_path.write_text(
                                json.dumps(weather_snapshot, ensure_ascii=False, indent=2),
                                encoding="utf-8",
                            )
                            result["weather_snapshot_path"] = str(weather_path)

                    st.session_state.result = result
                    st.session_state.run_log = captured_log
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
    if (
        st.session_state.result
        and should_show_cda_calibration(
            st.session_state.result,
            st.session_state.config,
        )
    ):
        render_cda_calibration_summary(
            st.session_state.result,
            st.session_state.config,
        )
    if st.session_state.get("developer_mode", False) and st.session_state.result:
        render_kernel_profile(st.session_state.result)
        render_fit_cache_debug(st.session_state.result)

    if st.session_state.developer_mode:
        render_developer_diagnostics(st.session_state.result, st.session_state.profile)
        with st.expander("Aktuelle Konfiguration anzeigen"):
            st.json(st.session_state.config)

    st.divider()
    st.caption(f"Bike Power Calculator · Version {APP_VERSION} · Build {BUILD_DATE} · Rechenkern {ENGINE_VERSION}")


if __name__ == "__main__":
    main()
