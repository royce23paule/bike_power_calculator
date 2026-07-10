from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

from defaults import FIELDS, GROUP_TITLES, defaults_dict


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
    if "last_loaded_json_name" not in st.session_state:
        st.session_state.last_loaded_json_name = None
    if "generate_pdf" not in st.session_state:
        st.session_state.generate_pdf = True
    if "generate_html_map" not in st.session_state:
        st.session_state.generate_html_map = True


def config_to_json_bytes(config: dict[str, Any]) -> bytes:
    return json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8")


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
    if not path_value:
        return path_value

    path = Path(path_value)
    if path.is_absolute():
        return str(path)

    candidate = Path(__file__).parent / path
    if candidate.exists():
        return str(candidate)

    return path_value


def render_sidebar() -> None:
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
        st.success("Version 1.7: refaktorierte Projektstruktur.")


def render_file_uploads(config: dict[str, Any]) -> dict[str, Any]:
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

    return config


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


def render_parameter_tabs(config: dict[str, Any]) -> dict[str, Any]:
    tab_keys = ["basis", "aero", "leistung", "wetter", "strecke", "ausgabe"]
    tabs = st.tabs([GROUP_TITLES[key] for key in tab_keys])

    updated = {}
    for tab, group_key in zip(tabs, tab_keys):
        with tab:
            updated.update(render_group(group_key, config))

    merged_config = config.copy()
    merged_config.update(updated)
    return normalize_loaded_config(merged_config)


def render_output_options() -> None:
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


def render_run_controls() -> bool:
    run_col, info_col = st.columns([1, 2])

    with run_col:
        start_clicked = st.button("Berechnung starten", type="primary", use_container_width=True)

    with info_col:
        if st.session_state.generate_pdf or st.session_state.generate_html_map:
            st.info("Die Berechnung erzeugt die ausgewählten Ausgaben. Für schnelle Tests kannst du PDF/Karte deaktivieren.")
        else:
            st.info("Schnellmodus aktiv: Es werden nur Berechnung und interaktive Diagramme erzeugt.")

    return start_clicked
