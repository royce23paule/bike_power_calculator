from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

from defaults import FIELDS, GROUP_TITLES, defaults_dict, ordered_values


st.set_page_config(
    page_title="Bike Power Calculator",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded",
)


def normalize_loaded_config(raw: dict[str, Any]) -> dict[str, Any]:
    """JSON-Konfiguration mit Defaults zusammenführen."""
    config = defaults_dict()
    for field in FIELDS:
        name = field["name"]
        if name in raw:
            config[name] = raw[name]
    return config


def init_session_state() -> None:
    if "config" not in st.session_state:
        st.session_state.config = defaults_dict()


def save_uploaded_file(uploaded_file) -> str | None:
    """Streamlit-Upload temporär speichern und Pfad zurückgeben.

    Die bestehende Berechnungslogik erwartet Dateipfade. Deshalb speichern wir
    Uploads serverseitig in ein temporäres Verzeichnis.
    """
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


def main() -> None:
    init_session_state()

    st.title("🚴 Bike Power Calculator")
    st.caption("Streamlit-Migration der bestehenden Desktop-App – Version 0.2")

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
        st.info("Version 0.2: vollständige Oberfläche. Die Berechnung wird im nächsten Schritt angebunden.")

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

    left, right = st.columns([1, 1])

    with left:
        if st.button("Berechnung starten", type="primary", use_container_width=True):
            st.warning(
                "Die Oberfläche ist vollständig vorbereitet. "
                "Die Anbindung an bike_power_calc.py folgt in Version 0.3."
            )
            st.write("Parameter in alter Reihenfolge:")
            st.code(repr(ordered_values(st.session_state.config)), language="python")

    with right:
        with st.expander("Aktuelle Konfiguration anzeigen"):
            st.json(st.session_state.config)


if __name__ == "__main__":
    main()
