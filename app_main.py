from __future__ import annotations

import contextlib
import io
import hashlib
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

APP_VERSION = "3.10.0"
BUILD_DATE = "2026-07-20"
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


def queue_loaded_config(config: dict[str, Any]) -> None:
    """Queue settings and open the calculator before creating its widgets.

    Streamlit removes widget state for widgets that are not rendered in the
    current run. Therefore loaded calculator values must only be written in a
    run that actually renders the calculator page.
    """
    normalized = normalize_loaded_config(config)
    st.session_state.config = normalized
    st.session_state.pending_loaded_config = normalized
    st.session_state.pending_app_main_area = "🚴 Rechner"


def apply_pending_navigation() -> None:
    pending_area = st.session_state.pop("pending_app_main_area", None)
    if pending_area:
        st.session_state["app_main_area"] = pending_area


def apply_pending_loaded_config_on_calculator() -> None:
    pending = st.session_state.pop("pending_loaded_config", None)
    if not isinstance(pending, dict):
        return
    for field in FIELDS:
        st.session_state.pop(widget_key(field), None)
    st.session_state.config = normalize_loaded_config(pending)
    sync_widgets_from_config(st.session_state.config)


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
    if "parameter_study" not in st.session_state:
        st.session_state.parameter_study = None
    if "parameter_study_2d" not in st.session_state:
        st.session_state.parameter_study_2d = None
    if "active_parameter_study" not in st.session_state:
        st.session_state.active_parameter_study = None
    if "active_parameter_study_type" not in st.session_state:
        st.session_state.active_parameter_study_type = None
    if "parameter_study_import_message" not in st.session_state:
        st.session_state.parameter_study_import_message = None
    if "github_study_selected_id" not in st.session_state:
        st.session_state.github_study_selected_id = None
    if "github_study_message" not in st.session_state:
        st.session_state.github_study_message = None


def config_to_json_bytes(config: dict[str, Any]) -> bytes:
    return json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8")


def _study_json_safe(value: Any) -> Any:
    """Convert simulation data recursively into portable JSON values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not np.isfinite(value):
            return None
        return value
    if isinstance(value, np.generic):
        return _study_json_safe(value.item())
    if isinstance(value, np.ndarray):
        return [_study_json_safe(item) for item in value.tolist()]
    if isinstance(value, pd.Series):
        return _study_json_safe(value.to_dict())
    if isinstance(value, pd.DataFrame):
        return [_study_json_safe(row) for row in value.to_dict(orient="records")]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _study_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_study_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def _study_export_payload(study: dict[str, Any], study_type: str, name: str) -> dict[str, Any]:
    payload = {
        "file_format": "BikePowerCalculator.ParameterStudy",
        "schema_version": 1,
        "app_version": APP_VERSION,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "study_type": study_type,
        "name": name.strip() or str(study.get("name") or "Parameterstudie"),
        "study": study,
    }
    return _study_json_safe(payload)


def _study_json_bytes(study: dict[str, Any], study_type: str, name: str) -> bytes:
    return json.dumps(
        _study_export_payload(study, study_type, name),
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    ).encode("utf-8")


def _safe_study_filename(name: str, study_type: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9ÄÖÜäöüß_-]+", "_", name.strip()).strip("_")
    if not stem:
        stem = f"Parameterstudie_{study_type}"
    return f"{stem}.study.json"


def _validate_loaded_study(raw: Any) -> tuple[str, dict[str, Any], str]:
    if not isinstance(raw, dict):
        raise ValueError("Die Datei enthält kein gültiges Studienobjekt.")
    if raw.get("file_format") != "BikePowerCalculator.ParameterStudy":
        raise ValueError("Die Datei ist keine Bike-Power-Calculator-Parameterstudie.")
    study_type = str(raw.get("study_type", ""))
    if study_type not in {"1D", "2D"}:
        raise ValueError("Unbekannter Studientyp. Erwartet wird 1D oder 2D.")
    study = raw.get("study")
    if not isinstance(study, dict) or not isinstance(study.get("runs"), list):
        raise ValueError("Die Studie enthält keine gültigen Simulationsläufe.")
    if not study.get("runs"):
        raise ValueError("Die Studie enthält keine Simulationsläufe.")
    if study_type == "1D" and not study.get("parameter"):
        raise ValueError("In der 1D-Studie fehlt der untersuchte Parameter.")
    if study_type == "2D" and (not study.get("x_parameter") or not study.get("y_parameter")):
        raise ValueError("In der 2D-Studie fehlen die Achsenparameter.")
    name = str(raw.get("name") or study.get("name") or "Geladene Parameterstudie")
    study["name"] = name
    study["loaded_from_app_version"] = raw.get("app_version")
    study["loaded_at"] = datetime.now().isoformat(timespec="seconds")
    return study_type, study, name


def set_active_parameter_study(
    study_type: str,
    study: dict[str, Any],
    *,
    github_study_id: str | None = None,
) -> None:
    """Set the single active study used by controls and result rendering."""
    normalized_type = "2D" if str(study_type).upper().startswith("2") else "1D"
    if normalized_type == "1D":
        st.session_state.parameter_study = study
    else:
        st.session_state.parameter_study_2d = study
    st.session_state.active_parameter_study = study
    st.session_state.active_parameter_study_type = normalized_type
    st.session_state.github_study_selected_id = github_study_id
    st.session_state.parameter_study_pending_type = (
        "2D – zwei Parameter" if normalized_type == "2D" else "1D – ein Parameter"
    )


def get_active_parameter_study() -> tuple[str, dict[str, Any] | None]:
    active_type = str(st.session_state.get("active_parameter_study_type") or "")
    active = st.session_state.get("active_parameter_study")
    if active_type in {"1D", "2D"} and isinstance(active, dict):
        return active_type, active

    selected = str(st.session_state.get("parameter_study_type", "1D – ein Parameter"))
    fallback_type = "2D" if selected.startswith("2D") else "1D"
    fallback_key = "parameter_study_2d" if fallback_type == "2D" else "parameter_study"
    fallback = st.session_state.get(fallback_key)
    return fallback_type, fallback if isinstance(fallback, dict) else None


def _load_study_into_session(
    raw: dict[str, Any],
    source_label: str = "",
    *,
    github_study_id: str | None = None,
) -> tuple[str, str]:
    loaded_type, loaded_study, loaded_name = _validate_loaded_study(raw)
    set_active_parameter_study(
        loaded_type,
        loaded_study,
        github_study_id=github_study_id,
    )
    st.session_state.parameter_study_import_message = f"Studie ‚{loaded_name}‘ ({loaded_type}) wurde {source_label or 'geladen'}."
    return loaded_type, loaded_name


def render_parameter_study_github_controls(
    study: dict[str, Any] | None,
    current_type: str,
    name: str,
) -> None:
    db = get_github_database()
    with st.expander("☁️ GitHub-Studienbibliothek", expanded=True):
        if db is None:
            st.info(
                "Die GitHub-Datenbank ist nicht konfiguriert. "
                "Der lokale JSON-Export bleibt verfügbar."
            )
            return

        try:
            studies = db.list_studies()
        except GitHubDatabaseError as exc:
            st.error(f"Studienbibliothek konnte nicht geladen werden: {exc}")
            return

        selected_id = st.session_state.get("github_study_selected_id")
        selected_exists = bool(
            selected_id
            and any(item.get("id") == selected_id for item in studies)
        )
        can_save = bool(isinstance(study, dict) and study.get("runs"))

        save_new_col, update_col, refresh_col = st.columns([2, 2, 1])
        with save_new_col:
            if st.button(
                "Als neue Studie speichern",
                use_container_width=True,
                disabled=not can_save,
                key=f"github_study_save_new_{current_type}",
            ):
                try:
                    payload = _study_export_payload(study, current_type, name)
                    meta = db.save_study(payload, name=name, study_id=None)
                    st.session_state.github_study_selected_id = meta["id"]
                    st.session_state.github_study_message = (
                        f"Neue Studie ‚{meta['name']}‘ wurde auf GitHub gespeichert."
                    )
                    st.rerun()
                except (GitHubDatabaseError, ValueError, TypeError) as exc:
                    st.error(f"Speichern fehlgeschlagen: {exc}")

        with update_col:
            if st.button(
                "Ausgewählte aktualisieren",
                use_container_width=True,
                disabled=not (can_save and selected_exists),
                key=f"github_study_update_{current_type}",
                help=(
                    "Überschreibt die aktuell ausgewählte GitHub-Studie. "
                    "Für eine zusätzliche Studie bitte „Als neue Studie speichern“ verwenden."
                ),
            ):
                try:
                    payload = _study_export_payload(study, current_type, name)
                    meta = db.save_study(
                        payload,
                        name=name,
                        study_id=selected_id,
                    )
                    st.session_state.github_study_selected_id = meta["id"]
                    st.session_state.github_study_message = (
                        f"Studie ‚{meta['name']}‘ wurde aktualisiert."
                    )
                    st.rerun()
                except (GitHubDatabaseError, ValueError, TypeError) as exc:
                    st.error(f"Aktualisieren fehlgeschlagen: {exc}")

        with refresh_col:
            if st.button(
                "Neu laden",
                use_container_width=True,
                key="github_study_refresh",
            ):
                st.rerun()

        message = st.session_state.get("github_study_message")
        if message:
            st.success(message)
            st.session_state.github_study_message = None

        if not studies:
            st.caption("Noch keine Studien auf GitHub gespeichert.")
            return

        st.markdown("#### Bibliothek")
        filter_col, sort_col, direction_col = st.columns([3, 2, 1.4])
        search = filter_col.text_input(
            "Suchen",
            key="github_study_search",
            placeholder="Name oder Parameter",
        ).strip().casefold()
        sort_mode = sort_col.selectbox(
            "Sortieren nach",
            ["Favoriten", "Änderungsdatum", "Erstellungsdatum", "Name", "Studientyp"],
            key="github_study_sort_mode",
        )
        descending = direction_col.selectbox(
            "Reihenfolge",
            ["Absteigend", "Aufsteigend"],
            key="github_study_sort_direction",
        ) == "Absteigend"

        filtered = [
            item
            for item in studies
            if (
                not search
                or search in str(item.get("name", "")).casefold()
                or search in str(item.get("parameter", "")).casefold()
                or search in str(item.get("x_parameter", "")).casefold()
                or search in str(item.get("y_parameter", "")).casefold()
                or search in str(item.get("study_type", "")).casefold()
            )
        ]

        def sort_value(item: dict[str, Any]) -> Any:
            if sort_mode == "Name":
                return str(item.get("name", "")).casefold()
            if sort_mode == "Studientyp":
                return (
                    str(item.get("study_type", "")).casefold(),
                    str(item.get("name", "")).casefold(),
                )
            if sort_mode == "Erstellungsdatum":
                return str(item.get("created_at", ""))
            if sort_mode == "Änderungsdatum":
                return str(item.get("updated_at", ""))
            return (
                bool(item.get("favorite")),
                str(item.get("updated_at", "")),
            )

        filtered.sort(key=sort_value, reverse=descending)

        if not filtered:
            st.info("Keine passende Studie gefunden.")
            return

        labels: dict[str, str] = {}
        for item in filtered:
            star = "⭐ " if item.get("favorite") else ""
            axes = item.get("parameter") or " × ".join(
                value
                for value in [
                    item.get("x_parameter"),
                    item.get("y_parameter"),
                ]
                if value
            )
            labels[item["id"]] = (
                f"{star}{item.get('name', 'Parameterstudie')} · "
                f"{item.get('study_type', '')} · {axes}"
            )

        ids = list(labels)
        selector_key = "github_study_selector_v393"
        stored_selector = st.session_state.get(selector_key)
        preferred_id = st.session_state.get("github_study_selected_id")
        if stored_selector not in ids:
            st.session_state[selector_key] = (
                preferred_id if preferred_id in ids else ids[0]
            )

        chosen = st.selectbox(
            "Gespeicherte Studie",
            ids,
            format_func=lambda value: labels[value],
            key=selector_key,
        )
        st.session_state.github_study_selected_id = chosen
        meta = next(item for item in filtered if item.get("id") == chosen)

        changed_at = str(meta.get("updated_at", ""))[:19].replace("T", " ")
        created_at = str(meta.get("created_at", ""))[:19].replace("T", " ")
        st.caption(
            f"{meta.get('run_count', 0)} Simulationen · "
            f"erstellt {created_at or '—'} · geändert {changed_at or '—'}"
        )

        action_1, action_2, action_3, action_4 = st.columns(4)
        if action_1.button(
            "Laden",
            type="primary",
            use_container_width=True,
            key=f"github_study_load_{chosen}",
        ):
            try:
                raw = db.load_study(chosen)
                _load_study_into_session(
                    raw,
                    "aus GitHub geladen",
                    github_study_id=chosen,
                )
                st.rerun()
            except (GitHubDatabaseError, ValueError) as exc:
                st.error(f"Laden fehlgeschlagen: {exc}")

        favorite_label = (
            "Favorit entfernen" if meta.get("favorite") else "Favorisieren"
        )
        if action_2.button(
            favorite_label,
            use_container_width=True,
            key=f"github_study_favorite_{chosen}",
        ):
            try:
                db.update_study_metadata(
                    chosen,
                    favorite=not bool(meta.get("favorite")),
                )
                st.rerun()
            except GitHubDatabaseError as exc:
                st.error(f"Änderung fehlgeschlagen: {exc}")

        if action_3.button(
            "Duplizieren",
            use_container_width=True,
            key=f"github_study_duplicate_{chosen}",
        ):
            try:
                copied = db.duplicate_study(
                    chosen,
                    name=f"{meta.get('name', 'Parameterstudie')} – Kopie",
                )
                st.session_state.github_study_selected_id = copied["id"]
                st.session_state[selector_key] = copied["id"]
                st.session_state.github_study_message = (
                    f"Studie wurde als ‚{copied['name']}‘ dupliziert."
                )
                st.rerun()
            except GitHubDatabaseError as exc:
                st.error(f"Duplizieren fehlgeschlagen: {exc}")

        if action_4.button(
            "Auswahl lösen",
            use_container_width=True,
            key=f"github_study_clear_selection_{chosen}",
            help=(
                "Die aktuelle Studie bleibt geöffnet, wird aber nicht mehr "
                "mit einer bestehenden GitHub-Studie verknüpft."
            ),
        ):
            st.session_state.github_study_selected_id = None
            st.session_state.pop(selector_key, None)
            st.rerun()

        st.markdown("#### Bearbeiten")
        rename_col, single_delete_col = st.columns(2)
        new_name = rename_col.text_input(
            "Neuer Name",
            value=str(meta.get("name", "")),
            key=f"github_study_rename_name_{chosen}",
        )
        if rename_col.button(
            "Umbenennen",
            use_container_width=True,
            disabled=not new_name.strip(),
            key=f"github_study_rename_{chosen}",
        ):
            try:
                renamed = db.update_study_metadata(
                    chosen,
                    name=new_name.strip(),
                )
                st.session_state.github_study_message = (
                    f"Studie wurde in ‚{renamed['name']}‘ umbenannt."
                )
                st.rerun()
            except GitHubDatabaseError as exc:
                st.error(f"Umbenennen fehlgeschlagen: {exc}")

        confirm_single = single_delete_col.checkbox(
            "Löschen bestätigen",
            key=f"github_study_delete_confirm_{chosen}",
        )
        if single_delete_col.button(
            "Ausgewählte Studie löschen",
            use_container_width=True,
            disabled=not confirm_single,
            key=f"github_study_delete_{chosen}",
        ):
            try:
                db.delete_studies([chosen])
                st.session_state.github_study_selected_id = None
                st.session_state.pop(selector_key, None)
                st.session_state.github_study_message = "Studie wurde gelöscht."
                st.rerun()
            except GitHubDatabaseError as exc:
                st.error(f"Löschen fehlgeschlagen: {exc}")

        with st.expander("Mehrere Studien auswählen und löschen"):
            multi_ids = st.multiselect(
                "Studien",
                ids,
                format_func=lambda value: labels[value],
                key="github_study_bulk_delete_selection",
            )
            confirm_bulk = st.checkbox(
                f"{len(multi_ids)} Studie(n) endgültig löschen",
                key="github_study_bulk_delete_confirm",
                disabled=not multi_ids,
            )
            if st.button(
                "Ausgewählte Studien löschen",
                use_container_width=True,
                disabled=not (multi_ids and confirm_bulk),
                key="github_study_bulk_delete",
            ):
                try:
                    deleted_count = db.delete_studies(multi_ids)
                    if st.session_state.get(
                        "github_study_selected_id"
                    ) in multi_ids:
                        st.session_state.github_study_selected_id = None
                    st.session_state.pop(selector_key, None)
                    st.session_state.github_study_bulk_delete_selection = []
                    st.session_state.github_study_bulk_delete_confirm = False
                    st.session_state.github_study_message = (
                        f"{deleted_count} Studie(n) wurden gelöscht."
                    )
                    st.rerun()
                except GitHubDatabaseError as exc:
                    st.error(f"Mehrfachlöschen fehlgeschlagen: {exc}")

def render_parameter_study_file_controls() -> None:
    st.markdown("### 💾 Studien speichern und laden")
    st.caption(
        "Der JSON-Export enthält die komplette Studie einschließlich Parameterbereichen, "
        "Referenzwerten, Konfigurationen und Simulationsergebnissen."
    )

    current_type, study = get_active_parameter_study()

    left, right = st.columns(2)
    with left:
        default_name = ""
        if isinstance(study, dict):
            default_name = str(study.get("name") or "")
            if not default_name:
                if current_type == "1D":
                    default_name = str(study.get("parameter") or "Parameterstudie")
                else:
                    default_name = f"{study.get('x_parameter', 'X')} × {study.get('y_parameter', 'Y')}"
        name = st.text_input(
            "Name der aktuellen Studie",
            value=default_name,
            key=f"parameter_study_export_name_{current_type.lower()}",
        )
        if isinstance(study, dict) and study.get("runs"):
            st.download_button(
                "Aktuelle Studie als JSON speichern",
                data=_study_json_bytes(study, current_type, name),
                file_name=_safe_study_filename(name, current_type),
                mime="application/json",
                use_container_width=True,
                key=f"parameter_study_json_download_{current_type.lower()}",
            )
        else:
            st.info(f"Noch keine {current_type}-Studie zum Speichern vorhanden.")

    render_parameter_study_github_controls(study, current_type, name)

    with right:
        uploaded = st.file_uploader(
            "Gespeicherte Studie laden",
            type=["json", "study"],
            key="parameter_study_json_upload",
            help="Unterstützt die von dieser App erzeugten *.study.json-Dateien.",
        )
        if uploaded is not None:
            if st.button(
                "Studie aus Datei übernehmen",
                type="primary",
                use_container_width=True,
                key="parameter_study_json_load_button",
            ):
                try:
                    raw = json.loads(uploaded.getvalue().decode("utf-8-sig"))
                    _load_study_into_session(raw)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Studie konnte nicht geladen werden: {exc}")

    message = st.session_state.get("parameter_study_import_message")
    if message:
        st.success(message)
        st.session_state.parameter_study_import_message = None


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

def _number_input_step(field: dict[str, Any], value: Any) -> float:
    """Choose a practical explicit step for Streamlit +/- controls."""
    name = str(field.get("name", "")).casefold()
    try:
        numeric_value = abs(float(value))
    except Exception:
        numeric_value = 0.0

    if "rollwiderstand" in name:
        return 0.0001
    if "cda" in name:
        return 0.01
    if "wirkungsgrad" in name:
        return 0.1
    if "abschwaechung" in name or "abschattung" in name:
        return 0.05
    if "temperatur" in name:
        return 0.5
    if "gewicht" in name:
        return 0.5
    if "leistung" in name or "[w]" in name:
        return 1.0
    if "steigung" in name or "[%]" in name:
        return 0.5
    if "windrichtung" in name:
        return 5.0
    if "windgeschwindigkeit" in name:
        return 1.0
    if numeric_value < 0.01:
        return 0.0001
    if numeric_value < 1:
        return 0.01
    if numeric_value < 10:
        return 0.1
    return 1.0


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
        return st.number_input(
            name,
            help=help_text,
            key=key,
            format="%.6g",
            step=_number_input_step(field, st.session_state[key]),
        )

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


def _parse_max_power_values(value: Any) -> list[float]:
    values = [
        float(item)
        for item in re.findall(r"-?\d+(?:\.\d+)?", str(value))
    ]
    return sorted(set(values))


def _optimization_is_active(config: dict[str, Any]) -> bool:
    try:
        target_np = float(config.get("Normalized Power Sollwert [W]", 0))
    except (TypeError, ValueError):
        target_np = 0.0
    return (
        target_np > 0
        and len(
            _parse_max_power_values(
                config.get("max. Leistung (Liste( [W]", "")
            )
        ) >= 2
    )


def _format_power_list(values: list[float]) -> str:
    formatted: list[str] = []
    for value in sorted(set(float(item) for item in values)):
        if float(value).is_integer():
            formatted.append(str(int(value)))
        else:
            formatted.append(f"{value:g}")
    return "[" + ",".join(formatted) + "]"


def _best_optimization_row(result: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    rows = result.get("optimization_results")
    if not isinstance(rows, list):
        return None
    valid = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("duration_s") is not None
    ]
    if not valid:
        return None
    return min(valid, key=lambda row: float(row["duration_s"]))


def _fine_power_values(
    best_power: float,
    radius_w: float,
    step_w: float,
) -> list[float]:
    if radius_w <= 0 or step_w <= 0:
        return []
    start = best_power - radius_w
    end = best_power + radius_w
    count = int(round((end - start) / step_w))
    return [
        round(start + index * step_w, 8)
        for index in range(count + 1)
        if start + index * step_w > 0
    ]


def run_single_simulation(
    config: dict[str, Any],
    *,
    generate_pdf: bool = False,
    generate_html_map: bool = False,
) -> dict[str, Any]:
    """Gemeinsamer Einstiegspunkt für Rechner, Studien und spätere Optimierer."""
    run_config = normalize_loaded_config(dict(config))
    run_config["GPX/FIT Datei"] = resolve_repository_path(
        str(run_config.get("GPX/FIT Datei", ""))
    )
    run_config["Wetterdatei Advanced Weather"] = resolve_repository_path(
        str(run_config.get("Wetterdatei Advanced Weather", ""))
    )
    return call_bike_power_calc(
        run_config,
        generate_pdf=generate_pdf,
        generate_html_map=generate_html_map,
    )


PARAMETER_STUDY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "CdA im Flachen": {
        "field": "cdA im Flachen [m^2]",
        "unit": "m²",
        "default_start": 0.205,
        "default_end": 0.225,
        "default_step": 0.002,
        "min": 0.10,
        "max": 0.60,
        "format": "%.3f",
        "min_step": 0.0001,
        "sensitivity_step": 0.001,
        "sensitivity_label": "0,001 m²",
    },
    "Leistung bei 0 % Steigung": {
        "field": "Leistung bei 0% Steigung [W]",
        "unit": "W",
        "default_start": 170.0,
        "default_end": 210.0,
        "default_step": 5.0,
        "min": 20.0,
        "max": 1000.0,
        "format": "%.1f",
        "min_step": 0.1,
        "sensitivity_step": 1.0,
        "sensitivity_label": "1 W",
    },
    "Fahrergewicht": {
        "field": "Gewicht Fahrer [kg]",
        "unit": "kg",
        "default_start": 70.0,
        "default_end": 78.0,
        "default_step": 1.0,
        "min": 20.0,
        "max": 250.0,
        "format": "%.1f",
        "min_step": 0.1,
        "sensitivity_step": 1.0,
        "sensitivity_label": "1 kg",
    },
    "Rollwiderstand Crr": {
        "field": "Rollwiderstand cr [-]",
        "unit": "",
        "default_start": 0.0025,
        "default_end": 0.0040,
        "default_step": 0.00025,
        "min": 0.0005,
        "max": 0.0200,
        "format": "%.5f",
        "min_step": 0.00001,
        "sensitivity_step": 0.0001,
        "sensitivity_label": "0,0001",
    },
}


def _parameter_study_values(
    start: float,
    end: float,
    step: float,
) -> list[float]:
    if step <= 0:
        raise ValueError("Die Schrittweite muss größer als null sein.")
    if end < start:
        raise ValueError("Der Endwert muss mindestens so groß wie der Startwert sein.")
    count = int(np.floor((end - start) / step + 1e-9)) + 1
    values = [start + index * step for index in range(count)]
    if values and values[-1] < end - max(abs(step) * 1e-8, 1e-12):
        values.append(end)
    return [float(value) for value in values]


def _set_parameter_study_value(
    config: dict[str, Any],
    definition: dict[str, Any],
    value: float,
) -> None:
    field = str(definition["field"])
    if field == "cdA im Flachen [m^2]":
        current = str(config.get(field, ""))
        parts = [part.strip() for part in current.split(",")]
        config[field] = (
            f"{value:.6g},{parts[1]}"
            if len(parts) > 1 and parts[1]
            else f"{value:.6g}"
        )
    else:
        config[field] = float(value)


def _parameter_study_summary_row(
    parameter_name: str,
    definition: dict[str, Any],
    value: float,
    result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "Parameter": parameter_name,
        "Wert": value,
        "Einheit": definition.get("unit", ""),
        "Zeit [s]": result.get("duration_s"),
        "Zeit": format_duration(result.get("duration_s")),
        "Ø Geschwindigkeit [km/h]": _comparison_metric_value(
            result,
            "average_speed_kmh",
            "calibration_speed_kmh",
        ),
        "Average Power [W]": _comparison_metric_value(
            result,
            "average_power_w",
            "calibration_ap",
        ),
        "Normalized Power [W]": _comparison_metric_value(
            result,
            "normalized_power_w",
            "calibration_np",
        ),
    }



def _parameter_study_reference_number(
    raw_value: Any,
    definition: dict[str, Any],
) -> float | None:
    try:
        if str(definition.get("field")) == "cdA im Flachen [m^2]":
            return float(str(raw_value).split(",")[0].strip())
        return float(raw_value)
    except (TypeError, ValueError):
        return None


def _parameter_study_seconds(value: Any) -> float | None:
    try:
        number = float(value)
        return number if np.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _format_signed_duration(seconds: float | None) -> str:
    if seconds is None or not np.isfinite(seconds):
        return "—"
    sign = "+" if seconds > 0 else "−" if seconds < 0 else "±"
    total = int(round(abs(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{sign}{hours}:{minutes:02d}:{secs:02d}"
    return f"{sign}{minutes}:{secs:02d}"


def _parameter_study_analysis_frame(study: dict[str, Any]) -> tuple[pd.DataFrame, int | None]:
    rows = []
    for run in study.get("runs", []):
        summary = dict(run.get("summary", {}))
        summary["Wert"] = run.get("value")
        rows.append(summary)
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame, None

    frame["Wert"] = pd.to_numeric(frame["Wert"], errors="coerce")
    frame["Zeit [s]"] = pd.to_numeric(frame.get("Zeit [s]"), errors="coerce")
    for column in [
        "Ø Geschwindigkeit [km/h]",
        "Average Power [W]",
        "Normalized Power [W]",
    ]:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    definition = study.get("definition", {})
    reference_number = _parameter_study_reference_number(
        study.get("reference_value"), definition
    )
    reference_index = None
    if reference_number is not None and frame["Wert"].notna().any():
        reference_index = int((frame["Wert"] - reference_number).abs().idxmin())
        reference_seconds = _parameter_study_seconds(
            frame.loc[reference_index, "Zeit [s]"]
        )
        if reference_seconds is not None:
            frame["Differenz zur Referenz [s]"] = frame["Zeit [s]"] - reference_seconds
            frame["Zeitgewinn zur Referenz [s]"] = reference_seconds - frame["Zeit [s]"]
    return frame.sort_values("Wert").reset_index(drop=True), reference_index


def _parameter_study_insight(
    study: dict[str, Any],
    frame: pd.DataFrame,
) -> str:
    valid = frame.dropna(subset=["Wert", "Zeit [s]"]).sort_values("Wert")
    if len(valid) < 2:
        return "Für ein automatisches Fazit werden mindestens zwei gültige Studienpunkte benötigt."

    first = valid.iloc[0]
    last = valid.iloc[-1]
    delta_parameter = float(last["Wert"] - first["Wert"])
    delta_time = float(last["Zeit [s]"] - first["Zeit [s]"])
    unit = str(study.get("definition", {}).get("unit", ""))
    parameter = str(study.get("parameter", "Parameter"))
    per_unit = delta_time / delta_parameter if abs(delta_parameter) > 1e-12 else None

    if delta_time > 0:
        direction = "verlängert"
    elif delta_time < 0:
        direction = "verkürzt"
    else:
        direction = "verändert"

    statement = (
        f"Eine Erhöhung von {parameter} von {first['Wert']:g} auf "
        f"{last['Wert']:g} {unit} {direction} die berechnete Fahrzeit um "
        f"{_format_signed_duration(abs(delta_time)).lstrip('+−±')}."
    )
    if per_unit is not None:
        statement += (
            f" Im untersuchten Bereich entspricht das im Mittel etwa "
            f"{abs(per_unit):.1f} Sekunden je {unit or 'Parametereinheit'}."
        )
    return statement



def _parameter_study_sensitivity(
    study: dict[str, Any],
    frame: pd.DataFrame,
) -> tuple[float | None, str]:
    valid = frame.dropna(subset=["Wert", "Zeit [s]"]).sort_values("Wert")
    if len(valid) < 2:
        return None, ""

    x = valid["Wert"].to_numpy(dtype=float)
    y = valid["Zeit [s]"].to_numpy(dtype=float)
    if np.ptp(x) <= 1e-12:
        return None, ""

    slope = float(np.polyfit(x, y, 1)[0])
    definition = study.get("definition", {})
    sensitivity_step = float(definition.get("sensitivity_step", 1.0))
    label = str(
        definition.get(
            "sensitivity_label",
            definition.get("unit", "Parametereinheit"),
        )
    )
    return slope * sensitivity_step, label


def _parameter_study_insights(
    study: dict[str, Any],
    frame: pd.DataFrame,
) -> list[str]:
    valid = frame.dropna(subset=["Wert", "Zeit [s]"]).sort_values("Wert")
    if len(valid) < 2:
        return [
            "Für automatische Kernaussagen werden mindestens zwei gültige Studienpunkte benötigt."
        ]

    parameter = str(study.get("parameter", "Parameter"))
    definition = study.get("definition", {})
    unit = str(definition.get("unit", ""))
    x = valid["Wert"].to_numpy(dtype=float)
    y = valid["Zeit [s]"].to_numpy(dtype=float)

    statements = [_parameter_study_insight(study, frame)]

    if len(valid) >= 3 and np.ptp(x) > 1e-12:
        coefficients = np.polyfit(x, y, 1)
        predicted = np.polyval(coefficients, x)
        residual_sum = float(np.sum((y - predicted) ** 2))
        total_sum = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1.0 - residual_sum / total_sum if total_sum > 1e-12 else 1.0

        if r_squared >= 0.995:
            statements.append(
                f"Der Zusammenhang zwischen {parameter} und Fahrzeit ist im "
                f"untersuchten Bereich nahezu linear (R² = {r_squared:.3f})."
            )
        elif r_squared >= 0.98:
            statements.append(
                f"Der Zusammenhang ist weitgehend linear, zeigt aber bereits "
                f"leichte Krümmung (R² = {r_squared:.3f})."
            )
        else:
            statements.append(
                f"Der Zusammenhang ist deutlich nichtlinear (R² = {r_squared:.3f}); "
                "ein einzelner Durchschnittswert beschreibt ihn nur eingeschränkt."
            )

        local_slopes = np.diff(y) / np.diff(x)
        if len(local_slopes) >= 2:
            first_abs = abs(float(local_slopes[0]))
            last_abs = abs(float(local_slopes[-1]))
            if first_abs > 1e-12:
                ratio = last_abs / first_abs
                if ratio < 0.75:
                    statements.append(
                        "Der zusätzliche Zeiteffekt wird zum oberen Ende des "
                        "untersuchten Bereichs deutlich kleiner."
                    )
                elif ratio > 1.25:
                    statements.append(
                        "Der zusätzliche Zeiteffekt wird zum oberen Ende des "
                        "untersuchten Bereichs deutlich größer."
                    )

    best = valid.loc[valid["Zeit [s]"].idxmin()]
    worst = valid.loc[valid["Zeit [s]"].idxmax()]
    statements.append(
        f"Zwischen der schnellsten Variante ({best['Wert']:g} {unit}) und der "
        f"langsamsten Variante ({worst['Wert']:g} {unit}) liegen "
        f"{format_duration(float(worst['Zeit [s]'] - best['Zeit [s]']))}."
    )
    return statements


def _add_reference_marker(
    fig: go.Figure,
    reference_row: pd.Series | None,
    *,
    y_column: str,
    name: str = "Referenz",
) -> None:
    if reference_row is None:
        return
    y_value = reference_row.get(y_column)
    if y_value is None or pd.isna(y_value):
        return
    fig.add_trace(
        go.Scatter(
            x=[float(reference_row["Wert"])],
            y=[float(y_value)],
            mode="markers",
            name=name,
            marker={"symbol": "star", "size": 16},
            hovertemplate=(
                "<b>Referenz</b><br>"
                "Parameter: %{x:g}<br>"
                "Wert: %{y:.2f}<extra></extra>"
            ),
        )
    )


def render_parameter_study_analysis(study: dict[str, Any]) -> None:
    frame, _ = _parameter_study_analysis_frame(study)
    if frame.empty:
        st.info("Für diese Studie liegen keine auswertbaren Ergebnisse vor.")
        return

    valid_time = frame.dropna(subset=["Zeit [s]"])
    if valid_time.empty:
        st.warning("Die Studienläufe enthalten keine auswertbaren Fahrzeiten.")
        return

    best_row = valid_time.loc[valid_time["Zeit [s]"].idxmin()]
    worst_row = valid_time.loc[valid_time["Zeit [s]"].idxmax()]
    reference_number = _parameter_study_reference_number(
        study.get("reference_value"), study.get("definition", {})
    )
    if reference_number is not None:
        reference_row = frame.loc[(frame["Wert"] - reference_number).abs().idxmin()]
    else:
        reference_row = None

    unit = str(study.get("definition", {}).get("unit", ""))
    parameter = str(study.get("parameter", "Parameter"))
    total_gain = float(worst_row["Zeit [s]"] - best_row["Zeit [s]"])
    sensitivity_seconds, sensitivity_label = _parameter_study_sensitivity(study, frame)

    kpis = st.columns(5)
    kpis[0].metric(
        "Schnellste Variante",
        f"{best_row['Wert']:g} {unit}".strip(),
        format_duration(best_row["Zeit [s]"]),
    )
    if reference_row is not None:
        kpis[1].metric(
            "Referenzpunkt",
            f"{reference_row['Wert']:g} {unit}".strip(),
            format_duration(reference_row["Zeit [s]"]),
            help="Nächstgelegener Studienpunkt zum aktuellen Rechnerwert.",
        )
        best_gain = float(reference_row["Zeit [s]"] - best_row["Zeit [s]"])
        kpis[2].metric(
            "Bestes Ergebnis vs. Referenz",
            _format_signed_duration(-best_gain),
        )
    else:
        kpis[1].metric("Referenzpunkt", "—")
        kpis[2].metric("Bestes Ergebnis vs. Referenz", "—")
    kpis[3].metric("Spannweite der Fahrzeit", format_duration(total_gain))
    if sensitivity_seconds is not None:
        kpis[4].metric(
            f"Effekt je {sensitivity_label}",
            _format_signed_duration(sensitivity_seconds),
            help=(
                "Mittlere lineare Sensitivität über den gesamten untersuchten Bereich. "
                "Positiv bedeutet längere, negativ kürzere Fahrzeit."
            ),
        )
    else:
        kpis[4].metric("Sensitivität", "—")

    with st.expander("Automatische Kernaussagen", expanded=True):
        for statement in _parameter_study_insights(study, frame):
            st.markdown(f"- {statement}")

    tabs = st.tabs(["Fahrzeit", "Geschwindigkeit", "Leistung", "Tabelle"])

    hover_columns = [
        "Zeit",
        "Differenz zur Referenz [s]",
        "Ø Geschwindigkeit [km/h]",
        "Average Power [W]",
        "Normalized Power [W]",
    ]
    hover_frame = frame.copy()
    for column in hover_columns:
        if column not in hover_frame:
            hover_frame[column] = np.nan
    customdata = hover_frame[hover_columns].to_numpy()

    with tabs[0]:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=frame["Wert"],
            y=frame["Zeit [s]"] / 60.0,
            mode="lines+markers",
            name="Fahrzeit",
            customdata=customdata,
            hovertemplate=(
                f"<b>{parameter}: %{{x:g}} {unit}</b><br>"
                "Fahrzeit: %{customdata[0]}<br>"
                "Δ Referenz: %{customdata[1]:+.0f} s<br>"
                "Ø Geschwindigkeit: %{customdata[2]:.2f} km/h<br>"
                "AP: %{customdata[3]:.1f} W<br>"
                "NP: %{customdata[4]:.1f} W"
                "<extra></extra>"
            ),
        ))
        if reference_row is not None:
            reference_for_minutes = reference_row.copy()
            reference_for_minutes["Zeit [min]"] = float(reference_row["Zeit [s]"]) / 60.0
            _add_reference_marker(
                fig,
                reference_for_minutes,
                y_column="Zeit [min]",
            )
            fig.add_vline(
                x=float(reference_row["Wert"]),
                line_dash="dash",
                annotation_text="Referenz",
                annotation_position="top",
            )
        fig.update_layout(
            xaxis_title=f"{parameter} [{unit}]" if unit else parameter,
            yaxis_title="Fahrzeit [min]",
            hovermode="closest",
        )
        st.plotly_chart(
            fig,
            use_container_width=True,
            key="parameter_study_time_chart",
        )

        if "Zeitgewinn zur Referenz [s]" in frame:
            gain_fig = go.Figure(go.Bar(
                x=frame["Wert"],
                y=frame["Zeitgewinn zur Referenz [s]"] / 60.0,
                name="Zeitgewinn",
                customdata=customdata,
                hovertemplate=(
                    f"<b>{parameter}: %{{x:g}} {unit}</b><br>"
                    "Zeitgewinn: %{y:.2f} min<br>"
                    "Fahrzeit: %{customdata[0]}<br>"
                    "Ø Geschwindigkeit: %{customdata[2]:.2f} km/h"
                    "<extra></extra>"
                ),
            ))
            gain_fig.add_hline(y=0)
            gain_fig.update_layout(
                xaxis_title=f"{parameter} [{unit}]" if unit else parameter,
                yaxis_title="Zeitgewinn zur Referenz [min]",
            )
            st.plotly_chart(
                gain_fig,
                use_container_width=True,
                key="parameter_study_gain_chart",
            )

    with tabs[1]:
        if "Ø Geschwindigkeit [km/h]" in frame:
            fig = go.Figure(go.Scatter(
                x=frame["Wert"],
                y=frame["Ø Geschwindigkeit [km/h]"],
                mode="lines+markers",
                name="Ø Geschwindigkeit",
                customdata=customdata,
                hovertemplate=(
                    f"<b>{parameter}: %{{x:g}} {unit}</b><br>"
                    "Ø Geschwindigkeit: %{y:.2f} km/h<br>"
                    "Fahrzeit: %{customdata[0]}<br>"
                    "Δ Referenz: %{customdata[1]:+.0f} s"
                    "<extra></extra>"
                ),
            ))
            _add_reference_marker(
                fig,
                reference_row,
                y_column="Ø Geschwindigkeit [km/h]",
            )
            if reference_row is not None:
                fig.add_vline(x=float(reference_row["Wert"]), line_dash="dash")
            fig.update_layout(
                xaxis_title=f"{parameter} [{unit}]" if unit else parameter,
                yaxis_title="Ø Geschwindigkeit [km/h]",
            )
            st.plotly_chart(
                fig,
                use_container_width=True,
                key="parameter_study_speed_chart",
            )

    with tabs[2]:
        fig = go.Figure()
        if "Average Power [W]" in frame:
            fig.add_trace(go.Scatter(
                x=frame["Wert"],
                y=frame["Average Power [W]"],
                mode="lines+markers",
                name="AP",
                customdata=customdata,
                hovertemplate=(
                    f"<b>{parameter}: %{{x:g}} {unit}</b><br>"
                    "AP: %{y:.1f} W<br>"
                    "NP: %{customdata[4]:.1f} W<br>"
                    "Fahrzeit: %{customdata[0]}"
                    "<extra></extra>"
                ),
            ))
        if "Normalized Power [W]" in frame:
            fig.add_trace(go.Scatter(
                x=frame["Wert"],
                y=frame["Normalized Power [W]"],
                mode="lines+markers",
                name="NP",
                customdata=customdata,
                hovertemplate=(
                    f"<b>{parameter}: %{{x:g}} {unit}</b><br>"
                    "NP: %{y:.1f} W<br>"
                    "AP: %{customdata[3]:.1f} W<br>"
                    "Fahrzeit: %{customdata[0]}"
                    "<extra></extra>"
                ),
            ))
        if reference_row is not None:
            fig.add_vline(
                x=float(reference_row["Wert"]),
                line_dash="dash",
                annotation_text="Referenz",
                annotation_position="top",
            )
        fig.update_layout(
            xaxis_title=f"{parameter} [{unit}]" if unit else parameter,
            yaxis_title="Leistung [W]",
            hovermode="closest",
        )
        st.plotly_chart(
            fig,
            use_container_width=True,
            key="parameter_study_power_chart",
        )

    with tabs[3]:
        display_frame = frame.copy()
        if "Differenz zur Referenz [s]" in display_frame:
            display_frame["Differenz zur Referenz"] = display_frame[
                "Differenz zur Referenz [s]"
            ].apply(_format_signed_duration)
        if reference_row is not None:
            display_frame["Referenz"] = np.isclose(
                display_frame["Wert"].astype(float),
                float(reference_row["Wert"]),
            )
        st.dataframe(display_frame, use_container_width=True, hide_index=True)
        st.download_button(
            "Studienergebnisse als CSV herunterladen",
            data=display_frame.to_csv(index=False).encode("utf-8"),
            file_name="parameterstudie.csv",
            mime="text/csv",
            use_container_width=True,
            key="parameter_study_csv",
        )


def render_parameter_study_1d() -> None:
    st.markdown("## 🧪 Eindimensionale Parameterstudie")
    st.caption(
        "Ein Eingabeparameter wird über einen Wertebereich variiert. "
        "Jede Variante verwendet exakt denselben Rechenkern wie der normale Rechner."
    )

    existing_study = st.session_state.get("parameter_study")
    if isinstance(existing_study, dict) and existing_study.get("runs"):
        st.markdown("### Aktive Studie")
        info_cols = st.columns(4)
        info_cols[0].metric("Parameter", existing_study.get("parameter", "—"))
        info_cols[1].metric("Simulationen", len(existing_study.get("runs", [])))
        info_cols[2].metric("Von", f"{existing_study.get('start', 0):g}")
        info_cols[3].metric("Bis", f"{existing_study.get('end', 0):g}")
        render_parameter_study_analysis(existing_study)
        st.divider()

    st.markdown("### Neue 1D-Studie berechnen")
    if not st.session_state.config.get("GPX/FIT Datei"):
        st.warning(
            "Zum Berechnen einer neuen Studie bitte im Rechner zuerst eine "
            "GPX- oder FIT-Strecke auswählen. Eine bereits geladene Studie bleibt oben sichtbar."
        )
        return

    @st.fragment
    def render_1d_study_controls() -> None:
        parameter_name = st.selectbox(
            "Parameter",
            list(PARAMETER_STUDY_DEFINITIONS.keys()),
            key="parameter_study_parameter",
        )
        definition = PARAMETER_STUDY_DEFINITIONS[parameter_name]
        signature = re.sub(
            r"[^a-z0-9]+",
            "_",
            parameter_name.lower(),
        ).strip("_")

        cols = st.columns(3)
        with cols[0]:
            start = st.number_input(
                "Von",
                min_value=float(definition["min"]),
                max_value=float(definition["max"]),
                value=float(definition["default_start"]),
                step=float(definition["min_step"]),
                format=str(definition["format"]),
                key=f"parameter_study_start_{signature}",
            )
        with cols[1]:
            end = st.number_input(
                "Bis",
                min_value=float(definition["min"]),
                max_value=float(definition["max"]),
                value=float(definition["default_end"]),
                step=float(definition["min_step"]),
                format=str(definition["format"]),
                key=f"parameter_study_end_{signature}",
            )
        with cols[2]:
            step = st.number_input(
                "Schrittweite",
                min_value=float(definition["min_step"]),
                value=float(definition["default_step"]),
                step=float(definition["min_step"]),
                format=str(definition["format"]),
                key=f"parameter_study_step_{signature}",
            )

        try:
            values = _parameter_study_values(
                float(start),
                float(end),
                float(step),
            )
        except ValueError as exc:
            st.error(str(exc))
            return

        unit = str(definition.get("unit", ""))
        st.metric("Anzahl Simulationen", len(values))
        if len(values) > 25:
            st.error(
                "Maximal sind 25 Simulationen pro eindimensionaler Studie erlaubt. "
                "Bitte Bereich oder Schrittweite anpassen."
            )
            return

        reference_config = dict(st.session_state.config)
        reference_raw = reference_config.get(str(definition["field"]))
        st.caption(
            f"Aktuelle Referenz aus dem Rechner: "
            f"{reference_raw} {unit}".strip()
        )

        if st.button(
            "Parameterstudie starten",
            type="primary",
            use_container_width=True,
            key="start_parameter_study",
        ):
            progress = st.progress(
                0,
                text="Parameterstudie wird vorbereitet …",
            )
            status = st.empty()
            study_runs: list[dict[str, Any]] = []
            started_at = datetime.now().isoformat(timespec="seconds")
            try:
                for index, value in enumerate(values):
                    config = dict(reference_config)
                    _set_parameter_study_value(config, definition, value)
                    config["Titel"] = (
                        f"Studie {parameter_name} = {value:g} {unit}".strip()
                    )
                    status.info(
                        f"Simulation {index + 1} von {len(values)}: "
                        f"{parameter_name} = {value:g} {unit}".strip()
                    )
                    with contextlib.redirect_stdout(
                        io.StringIO()
                    ), contextlib.redirect_stderr(io.StringIO()):
                        result = run_single_simulation(
                            config,
                            generate_pdf=False,
                            generate_html_map=False,
                        )
                    study_runs.append(
                        {
                            "value": value,
                            "config": config,
                            "result": result,
                            "summary": _parameter_study_summary_row(
                                parameter_name,
                                definition,
                                value,
                                result,
                            ),
                        }
                    )
                    progress.progress(
                        int((index + 1) / len(values) * 100),
                        text=(
                            f"{index + 1} von {len(values)} "
                            "Simulationen abgeschlossen"
                        ),
                    )

                new_study = {
                    "id": str(uuid.uuid4()),
                    "name": (
                        f"{parameter_name} {start:g}–{end:g} {unit}".strip()
                    ),
                    "created_at": started_at,
                    "study_schema_version": 1,
                    "source_app_version": APP_VERSION,
                    "parameter": parameter_name,
                    "definition": dict(definition),
                    "start": float(start),
                    "end": float(end),
                    "step": float(step),
                    "reference_value": reference_raw,
                    "runs": study_runs,
                }
                set_active_parameter_study(
                    "1D",
                    new_study,
                    github_study_id=None,
                )
                st.session_state.parameter_study_calculation_message = (
                    "1D-Parameterstudie abgeschlossen."
                )
                st.rerun(scope="app")
            except Exception as exc:
                progress.empty()
                status.empty()
                st.error(f"Parameterstudie abgebrochen: {exc}")
                with st.expander("Fehlerdetails", expanded=False):
                    st.code(traceback.format_exc())

    render_1d_study_controls()

    if not (
        isinstance(st.session_state.get("parameter_study"), dict)
        and st.session_state.parameter_study.get("runs")
    ):
        st.info("Noch keine Parameterstudie im aktuellen Browser-Sitzungsspeicher.")



def _parameter_study_2d_frame(study: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for run in study.get("runs", []):
        row = dict(run.get("summary", {}))
        row["X"] = run.get("x_value")
        row["Y"] = run.get("y_value")
        rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    for column in [
        "X", "Y", "Zeit [s]", "Ø Geschwindigkeit [km/h]",
        "Average Power [W]", "Normalized Power [W]",
    ]:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _format_heatmap_time(value: Any) -> str:
    seconds = _parameter_study_seconds(value)
    if seconds is None:
        return "—"
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def render_parameter_study_2d_analysis(study: dict[str, Any]) -> None:
    frame = _parameter_study_2d_frame(study)
    if frame.empty or frame["Zeit [s]"].dropna().empty:
        st.info("Für diese zweidimensionale Studie liegen keine auswertbaren Ergebnisse vor.")
        return

    x_name = str(study.get("x_parameter", "X"))
    y_name = str(study.get("y_parameter", "Y"))
    x_definition = study.get("x_definition", {})
    y_definition = study.get("y_definition", {})
    x_unit = str(x_definition.get("unit", ""))
    y_unit = str(y_definition.get("unit", ""))

    valid = frame.dropna(subset=["X", "Y", "Zeit [s]"])
    best = valid.loc[valid["Zeit [s]"].idxmin()]
    worst = valid.loc[valid["Zeit [s]"].idxmax()]

    x_reference = _parameter_study_reference_number(
        study.get("x_reference_value"), x_definition
    )
    y_reference = _parameter_study_reference_number(
        study.get("y_reference_value"), y_definition
    )
    reference_row = None
    if x_reference is not None and y_reference is not None:
        x_span = max(float(valid["X"].max() - valid["X"].min()), 1e-12)
        y_span = max(float(valid["Y"].max() - valid["Y"].min()), 1e-12)
        distance = ((valid["X"] - x_reference) / x_span) ** 2 + ((valid["Y"] - y_reference) / y_span) ** 2
        reference_row = valid.loc[distance.idxmin()]

    metrics = st.columns(4)
    metrics[0].metric(
        "Schnellste Kombination",
        f"{x_name}: {best['X']:g} {x_unit} | {y_name}: {best['Y']:g} {y_unit}".strip(),
        _format_heatmap_time(best["Zeit [s]"]),
    )
    metrics[1].metric("Zeitspanne", format_duration(float(worst["Zeit [s]"] - best["Zeit [s]"])))
    metrics[2].metric("Kombinationen", len(valid))
    if reference_row is not None:
        metrics[3].metric(
            "Referenzpunkt",
            f"{reference_row['X']:g} / {reference_row['Y']:g}",
            _format_heatmap_time(reference_row["Zeit [s]"]),
            help="Nächstgelegene berechnete Kombination zu den aktuellen Rechnerwerten.",
        )
    else:
        metrics[3].metric("Referenzpunkt", "—")

    tabs = st.tabs(["Fahrzeit-Heatmap", "Geschwindigkeit", "Tabelle"])
    x_values = sorted(valid["X"].unique())
    y_values = sorted(valid["Y"].unique())

    with tabs[0]:
        time_pivot = valid.pivot(index="Y", columns="X", values="Zeit [s]").reindex(index=y_values, columns=x_values)
        text = [[_format_heatmap_time(value) for value in row] for row in time_pivot.to_numpy()]
        fig = go.Figure(go.Heatmap(
            x=x_values,
            y=y_values,
            z=time_pivot.to_numpy() / 60.0,
            text=text,
            texttemplate="%{text}",
            customdata=time_pivot.to_numpy(),
            colorbar={"title": "Zeit [min]"},
            hovertemplate=(
                f"<b>{x_name}: %{{x:g}} {x_unit}</b><br>"
                f"{y_name}: %{{y:g}} {y_unit}<br>"
                "Fahrzeit: %{text}<br>"
                "Zeit: %{z:.2f} min<extra></extra>"
            ),
        ))
        if reference_row is not None:
            fig.add_trace(go.Scatter(
                x=[float(reference_row["X"])],
                y=[float(reference_row["Y"])],
                mode="markers",
                name="Referenz",
                marker={"symbol": "star", "size": 18},
                hovertemplate="<b>Referenz</b><br>X: %{x:g}<br>Y: %{y:g}<extra></extra>",
            ))
        fig.update_layout(
            xaxis_title=f"{x_name} [{x_unit}]" if x_unit else x_name,
            yaxis_title=f"{y_name} [{y_unit}]" if y_unit else y_name,
        )
        st.plotly_chart(fig, use_container_width=True, key="parameter_study_2d_time_heatmap")

    with tabs[1]:
        speed_pivot = valid.pivot(index="Y", columns="X", values="Ø Geschwindigkeit [km/h]").reindex(index=y_values, columns=x_values)
        fig = go.Figure(go.Heatmap(
            x=x_values,
            y=y_values,
            z=speed_pivot.to_numpy(),
            text=np.round(speed_pivot.to_numpy(), 2),
            texttemplate="%{text:.2f}",
            colorbar={"title": "km/h"},
            hovertemplate=(
                f"<b>{x_name}: %{{x:g}} {x_unit}</b><br>"
                f"{y_name}: %{{y:g}} {y_unit}<br>"
                "Ø Geschwindigkeit: %{z:.2f} km/h<extra></extra>"
            ),
        ))
        if reference_row is not None:
            fig.add_trace(go.Scatter(
                x=[float(reference_row["X"])], y=[float(reference_row["Y"])],
                mode="markers", name="Referenz", marker={"symbol": "star", "size": 18},
            ))
        fig.update_layout(
            xaxis_title=f"{x_name} [{x_unit}]" if x_unit else x_name,
            yaxis_title=f"{y_name} [{y_unit}]" if y_unit else y_name,
        )
        st.plotly_chart(fig, use_container_width=True, key="parameter_study_2d_speed_heatmap")

    with tabs[2]:
        display = valid.copy()
        display = display.rename(columns={"X": x_name, "Y": y_name})
        display["Zeit"] = display["Zeit [s]"].apply(_format_heatmap_time)
        if reference_row is not None:
            display["Referenz"] = np.isclose(display[x_name], float(reference_row["X"])) & np.isclose(display[y_name], float(reference_row["Y"]))
        ordered = [x_name, y_name, "Zeit", "Ø Geschwindigkeit [km/h]", "Average Power [W]", "Normalized Power [W]"]
        ordered += [column for column in display.columns if column not in ordered and column != "Zeit [s]"]
        display = display[[column for column in ordered if column in display.columns]]
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.download_button(
            "2D-Studie als CSV herunterladen",
            data=display.to_csv(index=False).encode("utf-8"),
            file_name="parameterstudie_2d.csv",
            mime="text/csv",
            use_container_width=True,
            key="parameter_study_2d_csv",
        )


def _render_parameter_range_inputs(
    parameter_name: str,
    definition: dict[str, Any],
    prefix: str,
) -> tuple[float, float, float, list[float]]:
    signature = re.sub(r"[^a-z0-9]+", "_", parameter_name.lower()).strip("_")
    cols = st.columns(3)
    with cols[0]:
        start = st.number_input(
            "Von", min_value=float(definition["min"]), max_value=float(definition["max"]),
            value=float(definition["default_start"]),
            step=float(definition["min_step"]),
            format=str(definition["format"]),
            key=f"{prefix}_start_{signature}",
        )
    with cols[1]:
        end = st.number_input(
            "Bis", min_value=float(definition["min"]), max_value=float(definition["max"]),
            value=float(definition["default_end"]),
            step=float(definition["min_step"]),
            format=str(definition["format"]),
            key=f"{prefix}_end_{signature}",
        )
    with cols[2]:
        step = st.number_input(
            "Schrittweite", min_value=float(definition["min_step"]),
            value=float(definition["default_step"]),
            step=float(definition["min_step"]),
            format=str(definition["format"]),
            key=f"{prefix}_step_{signature}",
        )
    values = _parameter_study_values(float(start), float(end), float(step))
    return float(start), float(end), float(step), values


def render_parameter_study_2d() -> None:
    st.markdown("## 🧭 Zweidimensionale Parameterstudie")
    st.caption(
        "Zwei Eingabeparameter werden gleichzeitig variiert. Die Heatmap zeigt, "
        "welche Kombinationen auf der gewählten Strecke besonders schnell sind."
    )

    existing_study = st.session_state.get("parameter_study_2d")
    if isinstance(existing_study, dict) and existing_study.get("runs"):
        st.markdown("### Aktive 2D-Studie")
        render_parameter_study_2d_analysis(existing_study)
        st.divider()

    st.markdown("### Neue 2D-Studie berechnen")
    if not st.session_state.config.get("GPX/FIT Datei"):
        st.warning(
            "Zum Berechnen einer neuen 2D-Studie bitte im Rechner zuerst eine "
            "GPX- oder FIT-Strecke auswählen. Eine bereits geladene Studie bleibt oben sichtbar."
        )
        return

    @st.fragment
    def render_2d_study_controls() -> None:
        names = list(PARAMETER_STUDY_DEFINITIONS.keys())
        select_cols = st.columns(2)
        with select_cols[0]:
            x_name = st.selectbox(
                "X-Parameter",
                names,
                index=0,
                key="parameter_study_2d_x",
            )
        with select_cols[1]:
            y_options = [name for name in names if name != x_name]
            y_name = st.selectbox(
                "Y-Parameter",
                y_options,
                index=0,
                key="parameter_study_2d_y",
            )

        x_definition = PARAMETER_STUDY_DEFINITIONS[x_name]
        y_definition = PARAMETER_STUDY_DEFINITIONS[y_name]

        with st.expander(f"Bereich X: {x_name}", expanded=True):
            try:
                x_start, x_end, x_step, x_values = (
                    _render_parameter_range_inputs(
                        x_name,
                        x_definition,
                        "study2d_x",
                    )
                )
            except ValueError as exc:
                st.error(str(exc))
                return

        with st.expander(f"Bereich Y: {y_name}", expanded=True):
            try:
                y_start, y_end, y_step, y_values = (
                    _render_parameter_range_inputs(
                        y_name,
                        y_definition,
                        "study2d_y",
                    )
                )
            except ValueError as exc:
                st.error(str(exc))
                return

        total = len(x_values) * len(y_values)
        metrics = st.columns(3)
        metrics[0].metric("X-Werte", len(x_values))
        metrics[1].metric("Y-Werte", len(y_values))
        metrics[2].metric("Simulationen", total)

        if len(x_values) > 8 or len(y_values) > 8 or total > 36:
            st.error(
                "Maximal sind 8 Werte je Achse und insgesamt 36 "
                "Simulationen erlaubt. Bitte Bereich oder Schrittweite anpassen."
            )
            return

        reference_config = dict(st.session_state.config)
        x_reference = reference_config.get(str(x_definition["field"]))
        y_reference = reference_config.get(str(y_definition["field"]))
        st.caption(
            f"Aktuelle Referenz: {x_name} = {x_reference} "
            f"{x_definition.get('unit', '')} | "
            f"{y_name} = {y_reference} {y_definition.get('unit', '')}"
        )
        st.caption(
            "Änderungen in diesem Bereich aktualisieren nur die Eingaben. "
            "Die vorhandene Heatmap wird dabei nicht neu aufgebaut."
        )

        if st.button(
            "2D-Parameterstudie starten",
            type="primary",
            use_container_width=True,
            key="start_parameter_study_2d",
        ):
            progress = st.progress(
                0,
                text="2D-Parameterstudie wird vorbereitet …",
            )
            status = st.empty()
            runs: list[dict[str, Any]] = []
            index = 0
            try:
                for y_value in y_values:
                    for x_value in x_values:
                        index += 1
                        config = dict(reference_config)
                        _set_parameter_study_value(
                            config,
                            x_definition,
                            x_value,
                        )
                        _set_parameter_study_value(
                            config,
                            y_definition,
                            y_value,
                        )
                        config["Titel"] = (
                            f"2D-Studie {x_name}={x_value:g}; "
                            f"{y_name}={y_value:g}"
                        )
                        status.info(
                            f"Simulation {index} von {total}: "
                            f"{x_name} = {x_value:g}, "
                            f"{y_name} = {y_value:g}"
                        )
                        with contextlib.redirect_stdout(
                            io.StringIO()
                        ), contextlib.redirect_stderr(io.StringIO()):
                            result = run_single_simulation(
                                config,
                                generate_pdf=False,
                                generate_html_map=False,
                            )
                        summary = _parameter_study_summary_row(
                            x_name,
                            x_definition,
                            x_value,
                            result,
                        )
                        summary["Y-Parameter"] = y_name
                        summary["Y-Wert"] = y_value
                        runs.append(
                            {
                                "x_value": x_value,
                                "y_value": y_value,
                                "config": config,
                                "result": result,
                                "summary": summary,
                            }
                        )
                        progress.progress(
                            int(index / total * 100),
                            text=(
                                f"{index} von {total} "
                                "Simulationen abgeschlossen"
                            ),
                        )

                new_study = {
                    "id": str(uuid.uuid4()),
                    "created_at": datetime.now().isoformat(
                        timespec="seconds"
                    ),
                    "name": f"{x_name} × {y_name}",
                    "study_schema_version": 1,
                    "source_app_version": APP_VERSION,
                    "x_parameter": x_name,
                    "y_parameter": y_name,
                    "x_definition": dict(x_definition),
                    "y_definition": dict(y_definition),
                    "x_start": x_start,
                    "x_end": x_end,
                    "x_step": x_step,
                    "y_start": y_start,
                    "y_end": y_end,
                    "y_step": y_step,
                    "x_reference_value": x_reference,
                    "y_reference_value": y_reference,
                    "runs": runs,
                }
                set_active_parameter_study(
                    "2D",
                    new_study,
                    github_study_id=None,
                )
                st.session_state.parameter_study_calculation_message = (
                    "2D-Parameterstudie abgeschlossen."
                )
                st.rerun(scope="app")
            except Exception as exc:
                progress.empty()
                status.empty()
                st.error(f"2D-Parameterstudie abgebrochen: {exc}")
                with st.expander("Fehlerdetails", expanded=False):
                    st.code(traceback.format_exc())

    render_2d_study_controls()

    if not (
        isinstance(st.session_state.get("parameter_study_2d"), dict)
        and st.session_state.parameter_study_2d.get("runs")
    ):
        st.info(
            "Noch keine zweidimensionale Parameterstudie "
            "im aktuellen Browser-Sitzungsspeicher."
        )



def render_parameter_study() -> None:
    calculation_message = st.session_state.pop(
        "parameter_study_calculation_message",
        None,
    )
    if calculation_message:
        st.success(calculation_message)

    pending_type = st.session_state.pop("parameter_study_pending_type", None)
    if pending_type in {"1D – ein Parameter", "2D – zwei Parameter"}:
        # The radio widget may already have existed in a previous run. Remove
        # its widget state before assigning the type of the loaded study.
        st.session_state.pop("parameter_study_type", None)
        st.session_state.parameter_study_type = pending_type

    study_type = st.radio(
        "Studientyp",
        ["1D – ein Parameter", "2D – zwei Parameter"],
        horizontal=True,
        key="parameter_study_type",
    )

    requested_type = "2D" if study_type.startswith("2D") else "1D"
    active_type = st.session_state.get("active_parameter_study_type")
    if active_type != requested_type:
        requested_key = (
            "parameter_study_2d" if requested_type == "2D" else "parameter_study"
        )
        requested_study = st.session_state.get(requested_key)
        st.session_state.active_parameter_study_type = requested_type
        st.session_state.active_parameter_study = (
            requested_study if isinstance(requested_study, dict) else None
        )
        st.session_state.github_study_selected_id = None

    render_parameter_study_file_controls()
    st.divider()

    active_type, active_study = get_active_parameter_study()
    if active_type == "1D":
        if isinstance(active_study, dict) and active_study.get("runs"):
            st.session_state.parameter_study = active_study
        render_parameter_study_1d()
    else:
        if isinstance(active_study, dict) and active_study.get("runs"):
            st.session_state.parameter_study_2d = active_study
        render_parameter_study_2d()



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

        zoom = st.slider("PDF-Vorschau Zoom", 1.0, 4.0, 2.5, 0.1)
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
                refresh_github_repository_statistics(db)
                st.success(
                    f"Berechnung „{metadata['name']}“ wurde gespeichert."
                )
                st.caption(f"Berechnungs-ID: {metadata['id']}")
            except (GitHubDatabaseError, TypeError, ValueError) as exc:
                st.error(f"Berechnung konnte nicht gespeichert werden: {exc}")


def render_pacing_optimization_results(
    result: dict[str, Any] | None,
) -> None:
    if not isinstance(result, dict):
        return

    raw_rows = result.get("optimization_results")
    if not isinstance(raw_rows, list):
        return

    rows = [
        dict(row)
        for row in raw_rows
        if isinstance(row, dict)
        and row.get("max_power_w") is not None
        and row.get("duration_s") is not None
    ]
    unique_powers = {
        float(row["max_power_w"])
        for row in rows
    }
    try:
        target_np = float(result.get("optimization_target_np_w", 0))
    except (TypeError, ValueError):
        target_np = 0.0

    if target_np <= 0 or len(unique_powers) < 2:
        return

    rows.sort(key=lambda row: float(row["max_power_w"]))
    best = min(rows, key=lambda row: float(row["duration_s"]))
    best_time = float(best["duration_s"])

    for row in rows:
        row["time_loss_s"] = float(row["duration_s"]) - best_time

    st.divider()
    st.subheader("Pacing-Optimierung")
    st.caption(
        "Vergleich der getesteten maximalen Leistungen bei identischem "
        "Normalized-Power-Sollwert."
    )

    summary_cols = st.columns(4)
    summary_cols[0].metric(
        "Optimale max. Leistung",
        f"{float(best['max_power_w']):g} W",
    )
    summary_cols[1].metric(
        "Leistung bei 0 %",
        f"{float(best.get('power_at_zero_grade_w', 0)):.1f} W",
    )
    summary_cols[2].metric(
        "Bestzeit",
        format_duration(best_time),
    )
    summary_cols[3].metric(
        "Ø Geschwindigkeit",
        f"{float(best.get('average_speed_kmh', 0)):.3f} km/h",
    )

    coarse_values = result.get("optimization_coarse_power_values")
    fine_applied = bool(result.get("optimization_fine_applied"))
    boundary = bool(result.get("optimization_best_at_coarse_boundary"))

    fine_note = result.get("optimization_fine_note")
    if fine_applied:
        st.success(
            "Die optionale Feinoptimierung wurde um das beste innere "
            "Grobergebnis ausgeführt."
        )
    elif fine_note:
        st.warning(str(fine_note))
    elif boundary and isinstance(coarse_values, list) and coarse_values:
        st.warning(
            "Das beste Grobergebnis liegt am Rand der vorgegebenen Liste. "
            "Der tatsächliche optimale Wert könnte außerhalb des getesteten "
            "Bereichs liegen; deshalb wurde die Feinoptimierung nicht automatisch "
            "nach außen erweitert."
        )

    table_rows: list[dict[str, Any]] = []
    for row in rows:
        ap = row.get("average_power_w")
        np_value = row.get("normalized_power_w")
        vi = row.get("variability_index")
        table_rows.append(
            {
                "Max. Leistung [W]": float(row["max_power_w"]),
                "Leistung bei 0 % [W]": float(
                    row.get("power_at_zero_grade_w", 0)
                ),
                "AP [W]": None if ap is None else float(ap),
                "NP [W]": None if np_value is None else float(np_value),
                "VI": None if vi is None else float(vi),
                "Ø Geschwindigkeit [km/h]": float(
                    row.get("average_speed_kmh", 0)
                ),
                "Fahrzeit": format_duration(float(row["duration_s"])),
                "Zeitverlust [s]": float(row["time_loss_s"]),
                "Optimum": (
                    "✓"
                    if float(row["max_power_w"])
                    == float(best["max_power_w"])
                    else ""
                ),
            }
        )

    frame = pd.DataFrame(table_rows)
    st.dataframe(
        frame.style.format(
            {
                "Max. Leistung [W]": "{:.1f}",
                "Leistung bei 0 % [W]": "{:.1f}",
                "AP [W]": "{:.1f}",
                "NP [W]": "{:.1f}",
                "VI": "{:.3f}",
                "Ø Geschwindigkeit [km/h]": "{:.3f}",
                "Zeitverlust [s]": "{:.1f}",
            },
            na_rep="—",
        ),
        use_container_width=True,
        hide_index=True,
    )

    chart_cols = st.columns(2)
    power_values = [float(row["max_power_w"]) for row in rows]
    speed_values = [float(row.get("average_speed_kmh", 0)) for row in rows]
    loss_values = [float(row["time_loss_s"]) for row in rows]

    speed_fig = go.Figure()
    speed_fig.add_trace(
        go.Scatter(
            x=power_values,
            y=speed_values,
            mode="lines+markers",
            name="Ø Geschwindigkeit",
            customdata=[
                [float(row["duration_s"]), float(row["time_loss_s"])]
                for row in rows
            ],
            hovertemplate=(
                "Max. Leistung: %{x:.1f} W<br>"
                "Ø Geschwindigkeit: %{y:.3f} km/h<br>"
                "Zeitverlust: %{customdata[1]:.1f} s<extra></extra>"
            ),
        )
    )
    speed_fig.update_layout(
        title="Geschwindigkeit abhängig von der maximalen Leistung",
        xaxis_title="Maximale Leistung [W]",
        yaxis_title="Ø Geschwindigkeit [km/h]",
        margin=dict(l=20, r=20, t=55, b=20),
    )
    chart_cols[0].plotly_chart(speed_fig, use_container_width=True)

    loss_fig = go.Figure()
    loss_fig.add_trace(
        go.Scatter(
            x=power_values,
            y=loss_values,
            mode="lines+markers",
            name="Zeitverlust",
            hovertemplate=(
                "Max. Leistung: %{x:.1f} W<br>"
                "Zeitverlust: %{y:.1f} s<extra></extra>"
            ),
        )
    )
    loss_fig.update_layout(
        title="Zeitverlust gegenüber dem Optimum",
        xaxis_title="Maximale Leistung [W]",
        yaxis_title="Zeitverlust [s]",
        margin=dict(l=20, r=20, t=55, b=20),
    )
    chart_cols[1].plotly_chart(loss_fig, use_container_width=True)

    @st.fragment
    def render_robust_range() -> None:
        default_tolerance = max(10.0, best_time * 0.0005)
        tolerance_s = st.number_input(
            "Toleranz für robusten Optimalbereich [s]",
            min_value=0.1,
            value=float(round(default_tolerance, 1)),
            step=1.0,
            help=(
                "Alle getesteten Varianten mit höchstens diesem Zeitverlust "
                "werden als praktisch gleichwertiger Optimalbereich angezeigt."
            ),
            key="pacing_optimization_tolerance_s",
        )
        robust_rows = [
            row
            for row in rows
            if float(row["time_loss_s"]) <= float(tolerance_s) + 1e-9
        ]
        if robust_rows:
            lower = min(float(row["max_power_w"]) for row in robust_rows)
            upper = max(float(row["max_power_w"]) for row in robust_rows)
            if lower == upper:
                range_text = f"{lower:g} W"
            else:
                range_text = f"{lower:g}–{upper:g} W"
            st.info(
                f"**Robuster Optimalbereich:** {range_text}  \n"
                f"Alle darin enthaltenen getesteten Varianten liegen höchstens "
                f"{float(tolerance_s):.1f} Sekunden hinter der Bestzeit."
            )

        five_second = [
            float(row["max_power_w"])
            for row in rows
            if float(row["time_loss_s"]) <= 5.0 + 1e-9
        ]
        fifteen_second = [
            float(row["max_power_w"])
            for row in rows
            if float(row["time_loss_s"]) <= 15.0 + 1e-9
        ]
        comparison_cols = st.columns(2)
        comparison_cols[0].metric(
            "Innerhalb von 5 s",
            (
                "—"
                if not five_second
                else (
                    f"{min(five_second):g} W"
                    if min(five_second) == max(five_second)
                    else f"{min(five_second):g}–{max(five_second):g} W"
                )
            ),
        )
        comparison_cols[1].metric(
            "Innerhalb von 15 s",
            (
                "—"
                if not fifteen_second
                else (
                    f"{min(fifteen_second):g} W"
                    if min(fifteen_second) == max(fifteen_second)
                    else f"{min(fifteen_second):g}–{max(fifteen_second):g} W"
                )
            ),
        )

    render_robust_range()


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

    render_pacing_optimization_results(result)

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



def refresh_github_repository_statistics(db) -> None:
    try:
        st.session_state.github_repository_statistics = db.repository_statistics()
    except GitHubDatabaseError:
        st.session_state.pop("github_repository_statistics", None)



COMPARISON_SERIES = {
    "Geschwindigkeit": {
        "keys": ["map_speed_kmh", "v"],
        "y_title": "Geschwindigkeit [km/h]",
    },
    "Leistung": {
        "keys": ["map_power_w", "power", "Power_fit"],
        "y_title": "Leistung [W]",
    },
    "Windgeschwindigkeit": {
        "keys": ["map_wind_kmh", "wind_speed_abs_List"],
        "y_title": "Wind [km/h]",
    },
    "Windkomponente längs": {
        "keys": ["map_wind_component_kmh", "v_w_List"],
        "y_title": "Windkomponente [km/h]",
    },
    "Relative Luftgeschwindigkeit": {
        "keys": ["map_air_speed_kmh", "air_speed_rel_List"],
        "y_title": "Relative Luftgeschwindigkeit [km/h]",
    },
    "Höhe": {
        "keys": ["map_elevation_m", "h", "h_raw"],
        "y_title": "Höhe [m]",
    },
    "Steigung": {
        "keys": ["map_grade_percent", "grade", "grade_raw"],
        "y_title": "Steigung [%]",
    },
    "Luftdichte": {
        "keys": ["rho_List"],
        "y_title": "Luftdichte [kg/m³]",
    },
    "CdA": {
        "keys": ["cdA_List"],
        "y_title": "CdA [m²]",
    },
}


def _first_series(result: dict[str, Any], keys: list[str]) -> list[float] | None:
    for key in keys:
        values = result.get(key)
        if values is None:
            continue
        try:
            array = np.asarray(values, dtype=float).reshape(-1)
        except Exception:
            continue
        if array.size < 2:
            continue
        return array.tolist()
    return None


def _comparison_distance_axis(
    result: dict[str, Any],
    series_length: int,
) -> tuple[np.ndarray, str]:
    for key in ("map_distance_km", "pos"):
        values = result.get(key)
        if values is None:
            continue
        try:
            distance = np.asarray(values, dtype=float).reshape(-1)
        except Exception:
            continue
        if distance.size == series_length:
            return distance, "Strecke [km]"

    if series_length <= 1:
        return np.asarray([0.0]), "Relative Strecke [%]"
    return np.linspace(0.0, 100.0, series_length), "Relative Strecke [%]"


def _comparison_metric_value(
    result: dict[str, Any],
    *keys: str,
) -> Any:
    for key in keys:
        value = result.get(key)
        if value is not None:
            return value
    return None


def build_comparison_summary(
    selected_results: list[dict[str, Any]],
) -> pd.DataFrame:
    rows = []
    for item in selected_results:
        result = item["result"]
        duration = _comparison_metric_value(result, "duration_s")
        row = {
            "Berechnung": item["name"],
            "Zeit": format_duration(duration),
            "Zeit [s]": duration,
            "Distanz [km]": _comparison_metric_value(
                result,
                "distance_km",
            ),
            "Ø Geschwindigkeit [km/h]": _comparison_metric_value(
                result,
                "average_speed_kmh",
                "calibration_speed_kmh",
            ),
            "AP [W]": _comparison_metric_value(
                result,
                "average_power_w",
                "calibration_ap",
            ),
            "NP [W]": _comparison_metric_value(
                result,
                "normalized_power_w",
                "calibration_np",
            ),
            "CdA [m²]": _comparison_metric_value(
                result,
                "calibration_cda",
            ),
            "Höhenmeter [m]": _comparison_metric_value(
                result,
                "elevation_gain_m",
            ),
            "Wettermodell": result.get("weather_source_mode"),
            "App-Version": result.get("app_version"),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def render_saved_calculation_comparison(
    db,
    event_id: str,
    calculations: list[dict[str, Any]],
    *,
    show_summary_section: bool = True,
    show_series_section: bool = True,
    show_difference_section: bool = True,
    key_prefix: str = "comparison",
) -> None:
    valid_calculations = [
        item for item in calculations
        if item.get("_integrity", {}).get("status") == "ok"
    ]
    if len(valid_calculations) < 2:
        st.info(
            "Für einen Vergleich werden mindestens zwei vollständige "
            "gespeicherte Berechnungen benötigt."
        )
        return

    label_to_id = {}
    metadata_by_id = {}
    for item in valid_calculations:
        calculation_id = item.get("id")
        label = (
            f"{item.get('name', calculation_id)} · "
            f"{str(item.get('created_at', ''))[:16].replace('T', ' ')}"
        )
        if label in label_to_id:
            label = f"{label} · {calculation_id}"
        label_to_id[label] = calculation_id
        metadata_by_id[calculation_id] = item

    default_labels = list(label_to_id.keys())[: min(3, len(label_to_id))]
    selected_labels = st.multiselect(
        "Berechnungen auswählen",
        options=list(label_to_id.keys()),
        default=default_labels,
        key=f"{key_prefix}_selection_{event_id}",
        help="Mindestens zwei, maximal acht Berechnungen auswählen.",
    )

    if len(selected_labels) < 2:
        st.info("Bitte mindestens zwei Berechnungen auswählen.")
        return
    if len(selected_labels) > 8:
        st.warning("Für eine übersichtliche Darstellung werden maximal acht Berechnungen verwendet.")
        selected_labels = selected_labels[:8]

    selection_signature = "|".join(label_to_id[label] for label in selected_labels)
    cache_key = f"{key_prefix}_results_{event_id}"
    signature_key = f"{key_prefix}_signature_{event_id}"

    if (
        st.session_state.get(signature_key) != selection_signature
        or cache_key not in st.session_state
    ):
        loaded_results = []
        try:
            with st.spinner("Gespeicherte Berechnungen werden geladen …"):
                for label in selected_labels:
                    calculation_id = label_to_id[label]
                    result = db.load_calculation_json(
                        event_id,
                        calculation_id,
                        "result.json",
                    )
                    loaded_results.append(
                        {
                            "id": calculation_id,
                            "name": metadata_by_id[calculation_id].get(
                                "name",
                                calculation_id,
                            ),
                            "metadata": metadata_by_id[calculation_id],
                            "result": result,
                        }
                    )
            st.session_state[cache_key] = loaded_results
            st.session_state[signature_key] = selection_signature
        except GitHubDatabaseError as exc:
            st.error(f"Vergleichsdaten konnten nicht geladen werden: {exc}")
            return

    selected_results = st.session_state.get(cache_key, [])
    if len(selected_results) < 2:
        return

    if show_summary_section:
        st.markdown("### Kennzahlenvergleich")
        summary_df = build_comparison_summary(selected_results)

        display_columns = [
            "Berechnung",
            "Zeit",
            "Distanz [km]",
            "Ø Geschwindigkeit [km/h]",
            "AP [W]",
            "NP [W]",
            "CdA [m²]",
            "Höhenmeter [m]",
            "Wettermodell",
        ]
        available_columns = [
            column for column in display_columns
            if column in summary_df.columns
        ]
        st.dataframe(
            summary_df[available_columns],
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "Vergleichstabelle als CSV herunterladen",
            data=summary_df.to_csv(index=False).encode("utf-8"),
            file_name="berechnungsvergleich.csv",
            mime="text/csv",
            use_container_width=True,
        )

        numeric_options = {
            "Fahrzeit [min]": (
                "duration_s",
                lambda value: float(value) / 60.0,
            ),
            "Ø Geschwindigkeit [km/h]": (
                "average_speed_kmh",
                float,
            ),
            "Average Power [W]": (
                "average_power_w",
                float,
            ),
            "Normalized Power [W]": (
                "normalized_power_w",
                float,
            ),
            "CdA [m²]": (
                "calibration_cda",
                float,
            ),
        }
        overview_metric = st.selectbox(
            "Kennzahl für Balkenvergleich",
            list(numeric_options.keys()),
            key=f"{key_prefix}_metric_{event_id}",
        )
        metric_key, converter = numeric_options[overview_metric]
        bar_rows = []
        for item in selected_results:
            result = item["result"]
            value = result.get(metric_key)
            if value is None and metric_key == "average_power_w":
                value = result.get("calibration_ap")
            if value is None and metric_key == "normalized_power_w":
                value = result.get("calibration_np")
            if value is None:
                continue
            try:
                value = converter(value)
            except Exception:
                continue
            bar_rows.append(
                {
                    "Berechnung": item["name"],
                    overview_metric: value,
                }
            )
        if bar_rows:
            bar_df = pd.DataFrame(bar_rows).set_index("Berechnung")
            st.bar_chart(bar_df)

    if show_series_section:
        st.markdown("### Gemeinsame Verlaufskurven")
        series_name = st.selectbox(
            "Zeitreihe auswählen",
            list(COMPARISON_SERIES.keys()),
            key=f"{key_prefix}_series_{event_id}",
        )
        series_definition = COMPARISON_SERIES[series_name]

        figure = go.Figure()
        added = 0
        x_title = "Strecke [km]"
        for item in selected_results:
            values = _first_series(
                item["result"],
                series_definition["keys"],
            )
            if values is None:
                continue

            y_values = np.asarray(values, dtype=float)
            x_values, current_x_title = _comparison_distance_axis(
                item["result"],
                len(y_values),
            )
            x_title = current_x_title

            valid = np.isfinite(x_values) & np.isfinite(y_values)
            if not np.any(valid):
                continue

            max_points = 2500
            valid_x = x_values[valid]
            valid_y = y_values[valid]
            if valid_x.size > max_points:
                indices = np.linspace(
                    0,
                    valid_x.size - 1,
                    max_points,
                ).astype(int)
                valid_x = valid_x[indices]
                valid_y = valid_y[indices]

            figure.add_trace(
                go.Scatter(
                    x=valid_x,
                    y=valid_y,
                    mode="lines",
                    name=item["name"],
                    hovertemplate=(
                        "%{x:.2f}<br>%{y:.2f}<extra>%{fullData.name}</extra>"
                    ),
                )
            )
            added += 1

        if added:
            figure.update_layout(
                xaxis_title=x_title,
                yaxis_title=series_definition["y_title"],
                legend_title="Berechnung",
                hovermode="x unified",
                height=560,
                margin=dict(l=20, r=20, t=30, b=20),
            )
            st.plotly_chart(
                figure,
                use_container_width=True,
                key=f"{key_prefix}_chart_{event_id}_{series_name}",
            )
        else:
            st.info(
                f"Für „{series_name}“ sind in den ausgewählten Berechnungen "
                "keine vergleichbaren Zeitreihen gespeichert."
            )

    if show_difference_section:
        st.markdown("### Differenzen zur Referenz")
        reference_name = st.selectbox(
            "Referenzberechnung",
            [item["name"] for item in selected_results],
            key=f"{key_prefix}_reference_{event_id}",
        )
        reference = next(
            item for item in selected_results
            if item["name"] == reference_name
        )
        reference_result = reference["result"]
        difference_rows = []
        for item in selected_results:
            result = item["result"]
            duration_delta = None
            speed_delta = None
            ap_delta = None
            np_delta = None

            if (
                result.get("duration_s") is not None
                and reference_result.get("duration_s") is not None
            ):
                duration_delta = (
                    float(result["duration_s"])
                    - float(reference_result["duration_s"])
                )
            if (
                result.get("average_speed_kmh") is not None
                and reference_result.get("average_speed_kmh") is not None
            ):
                speed_delta = (
                    float(result["average_speed_kmh"])
                    - float(reference_result["average_speed_kmh"])
                )

            result_ap = _comparison_metric_value(
                result,
                "average_power_w",
                "calibration_ap",
            )
            reference_ap = _comparison_metric_value(
                reference_result,
                "average_power_w",
                "calibration_ap",
            )
            if result_ap is not None and reference_ap is not None:
                ap_delta = float(result_ap) - float(reference_ap)

            result_np = _comparison_metric_value(
                result,
                "normalized_power_w",
                "calibration_np",
            )
            reference_np = _comparison_metric_value(
                reference_result,
                "normalized_power_w",
                "calibration_np",
            )
            if result_np is not None and reference_np is not None:
                np_delta = float(result_np) - float(reference_np)

            difference_rows.append(
                {
                    "Berechnung": item["name"],
                    "Δ Zeit [s]": duration_delta,
                    "Δ Geschwindigkeit [km/h]": speed_delta,
                    "Δ AP [W]": ap_delta,
                    "Δ NP [W]": np_delta,
                }
            )

        st.dataframe(
            pd.DataFrame(difference_rows),
            use_container_width=True,
            hide_index=True,
        )


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

    if st.button(
        "Repository-Statistik aktualisieren",
        key="github_db_statistics_refresh",
        use_container_width=True,
    ):
        try:
            with st.spinner("Repository wird analysiert …"):
                st.session_state.github_repository_statistics = db.repository_statistics()
        except GitHubDatabaseError as exc:
            st.error(f"Statistik konnte nicht erstellt werden: {exc}")

    repository_stats = st.session_state.get("github_repository_statistics")
    if repository_stats:
        cols = st.columns(2)
        cols[0].metric("Events", repository_stats.get("event_count", 0))
        cols[1].metric("Berechnungen", repository_stats.get("calculation_count", 0))
        cols[0].metric("Dateien", repository_stats.get("file_count", 0))
        cols[1].metric(
            "Speicher",
            f"{repository_stats.get('size_bytes', 0) / (1024 ** 2):.2f} MB",
        )
        largest = repository_stats.get("largest_file")
        if largest:
            st.caption(
                f"Größte Datei: {largest.get('path')} · "
                f"{largest.get('size_bytes', 0) / (1024 ** 2):.2f} MB"
            )

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

    tabs = st.tabs(["Events", "Neu", "Bearbeiten", "Dateien", "Berechnungen", "Backup"])

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
                    refresh_github_repository_statistics(db)
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
                            settings=None,
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
                try:
                    delete_files = db.list_event_files(selected_id)
                    delete_calculations = db.list_calculations(selected_id)
                except GitHubDatabaseError:
                    delete_files = []
                    delete_calculations = []

                st.warning(
                    f"Beim Löschen von „{event.get('name', selected_id)}“ werden "
                    f"{len(delete_calculations)} Berechnung(en), "
                    f"{len(delete_files)} sichtbare Event-Datei(en) sowie alle "
                    f"zugehörigen PDF-, HTML-, Wetter- und Systemdateien dauerhaft entfernt."
                )
                confirm_delete = st.checkbox(
                    "Ich bestätige die vollständige und dauerhafte Löschung",
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
                        with st.spinner(
                            "Event und alle zugehörigen Daten werden gelöscht …"
                        ):
                            db.delete_event(selected_id)
                        st.session_state.github_database_selected_event = None
                        refresh_github_repository_statistics(db)
                        st.success(
                            "Event einschließlich aller Berechnungen wurde gelöscht."
                        )
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
                file_df["type"] = file_df["name"].map(
                    lambda name: Path(str(name)).suffix.lower().lstrip(".").upper() or "DATEI"
                )
                if "storage" not in file_df.columns:
                    file_df["storage"] = "direct"
                st.dataframe(
                    file_df[["name", "type", "size_kb", "storage"]].rename(
                        columns={
                            "name": "Datei",
                            "type": "Typ",
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
                    checksum = hashlib.sha256(content).hexdigest()
                    st.caption(
                        f"Größe: {len(content) / 1024:.2f} KB · "
                        f"SHA-256: `{checksum}`"
                    )

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
                            key=f"github_load_json_file_{selected_id}_{selected_file}",
                            use_container_width=True,
                        ):
                            try:
                                loaded = json.loads(content.decode("utf-8-sig"))
                                if loaded.get("schema") == "bike_power_weather_snapshot":
                                    runtime_dir = Path(tempfile.gettempdir()) / "bike_power_event_files"
                                    runtime_dir.mkdir(parents=True, exist_ok=True)
                                    target = runtime_dir / Path(selected_file).name
                                    target.write_bytes(content)
                                    config = dict(st.session_state.config)
                                    config["Wetterdatei Advanced Weather"] = str(target)
                                    st.session_state.config = normalize_loaded_config(config)
                                    sync_widgets_from_config(st.session_state.config)
                                    st.success("Online-Wetter-Snapshot wurde in die App geladen.")
                                else:
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
                            key=f"github_load_data_file_{selected_id}_{selected_file}",
                            use_container_width=True,
                        ):
                            runtime_dir = Path(tempfile.gettempdir()) / "bike_power_event_files"
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

                    new_filename = st.text_input(
                        "Neuer Dateiname",
                        value=selected_file,
                        key=f"github_rename_file_name_{selected_id}_{selected_file}",
                    )
                    if action_cols[1].button(
                        "Datei umbenennen",
                        key=f"github_rename_file_{selected_id}_{selected_file}",
                        use_container_width=True,
                    ):
                        try:
                            renamed = db.rename_event_file(
                                selected_id,
                                selected_file,
                                new_filename,
                            )
                            st.success(f"Datei wurde in {renamed} umbenannt.")
                            st.rerun()
                        except GitHubDatabaseError as exc:
                            st.error(str(exc))

                    st.markdown("**Datei löschen**")
                    confirm_file_delete = st.checkbox(
                        f"„{selected_file}“ dauerhaft löschen",
                        key=f"github_confirm_delete_file_{selected_id}_{selected_file}",
                    )
                    if st.button(
                        "Datei dauerhaft löschen",
                        key=f"github_delete_file_{selected_id}_{selected_file}",
                        disabled=not confirm_file_delete,
                        use_container_width=True,
                    ):
                        try:
                            db.delete_event_file(selected_id, selected_file)
                            st.success(f"{selected_file} wurde gelöscht.")
                            st.rerun()
                        except GitHubDatabaseError as exc:
                            st.error(str(exc))

            st.divider()
            st.markdown("**Event-Backup**")
            st.caption(
                "Exportiert event.json, Eingabedateien, Einstellungen, Wetterdaten "
                "und alle gespeicherten Berechnungen als ZIP."
            )
            if st.button(
                "Event-ZIP vorbereiten",
                key=f"github_prepare_event_zip_{selected_id}",
                use_container_width=True,
            ):
                try:
                    with st.spinner("Event-Backup wird erstellt …"):
                        backup_name, backup_content = db.export_event_zip(selected_id)
                    st.session_state[f"github_event_zip_{selected_id}"] = (
                        backup_name,
                        backup_content,
                    )
                    st.success("Event-Backup wurde erstellt.")
                except GitHubDatabaseError as exc:
                    st.error(f"Event-Backup konnte nicht erstellt werden: {exc}")

            backup = st.session_state.get(f"github_event_zip_{selected_id}")
            if backup:
                backup_name, backup_content = backup
                st.download_button(
                    "Gesamtes Event als ZIP herunterladen",
                    data=backup_content,
                    file_name=backup_name,
                    mime="application/zip",
                    use_container_width=True,
                )

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

                integrity = metadata.get("_integrity", {})
                if integrity.get("status") == "ok":
                    st.success("Integritätsprüfung: vollständig")
                else:
                    missing = sorted(set(
                        integrity.get("missing_required", [])
                        + integrity.get("missing_declared", [])
                    ))
                    st.error(
                        "Integritätsprüfung: beschädigt oder unvollständig"
                        + (f" · fehlt: {', '.join(missing)}" if missing else "")
                    )
                if integrity.get("missing_recommended"):
                    st.warning(
                        "Optionale Dateien fehlen: "
                        + ", ".join(integrity["missing_recommended"])
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

                calculation_damaged = integrity.get("status") != "ok"
                action_cols = st.columns(3)

                if action_cols[0].button(
                    "Ergebnisse laden",
                    key=f"github_load_results_{calculation_id}",
                    disabled=calculation_damaged,
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
                    disabled=calculation_damaged,
                    use_container_width=True,
                ):
                    try:
                        settings = db.load_calculation_json(
                            selected_id,
                            calculation_id,
                            "settings_snapshot.json",
                        )
                        loaded_config = normalize_loaded_config(settings)
                        queue_loaded_config(loaded_config)
                        st.session_state.database_load_message = (
                            "Einstellungen wurden geladen und im Rechner übernommen."
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Einstellungen konnten nicht geladen werden: {exc}")

                if action_cols[2].button(
                    "Alles laden",
                    key=f"github_load_all_{calculation_id}",
                    type="primary",
                    disabled=calculation_damaged,
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
                        queue_loaded_config(loaded_config)
                        st.session_state.database_load_message = (
                            "Berechnung wurde vollständig geladen und im Rechner übernommen."
                        )
                        st.session_state.result = loaded_result
                        st.session_state.profile = loaded_profile
                        st.session_state.run_log = loaded_log
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Berechnung konnte nicht geladen werden: {exc}")

                st.divider()
                st.markdown("**Berechnung umbenennen**")
                renamed_calculation_name = st.text_input(
                    "Neuer Name",
                    value=metadata.get("name", ""),
                    key=f"github_rename_calc_name_{calculation_id}",
                )
                if st.button(
                    "Berechnungsnamen speichern",
                    key=f"github_rename_calc_{calculation_id}",
                    use_container_width=True,
                ):
                    try:
                        with st.spinner("Berechnung wird umbenannt …"):
                            db.rename_calculation(
                                selected_id,
                                calculation_id,
                                renamed_calculation_name,
                            )
                        st.success("Berechnung wurde umbenannt.")
                        st.rerun()
                    except GitHubDatabaseError as exc:
                        st.error(f"Umbenennen fehlgeschlagen: {exc}")

                st.divider()
                confirm_delete = st.checkbox(
                    "Löschen bestätigen",
                    key=f"github_confirm_delete_calc_{calculation_id}",
                    help=(
                        "Die komplette gespeicherte Berechnung einschließlich "
                        "Ergebnis, Einstellungen, Log, PDF und HTML wird gelöscht."
                    ),
                )
                if st.button(
                    "Berechnung dauerhaft löschen",
                    key=f"github_delete_calc_{calculation_id}",
                    disabled=not confirm_delete,
                    use_container_width=True,
                ):
                    try:
                        with st.spinner("Berechnung wird gelöscht …"):
                            db.delete_calculation(
                                selected_id,
                                calculation_id,
                            )
                        refresh_github_repository_statistics(db)
                        st.success("Berechnung wurde dauerhaft gelöscht.")
                        st.rerun()
                    except GitHubDatabaseError as exc:
                        st.error(f"Berechnung konnte nicht gelöscht werden: {exc}")

                with st.expander("Metadaten anzeigen", expanded=False):
                    st.json(metadata)


    with tabs[5]:
        st.markdown("**Event-ZIP importieren**")
        backup_upload = st.file_uploader(
            "Event-Backup auswählen",
            type=["zip"],
            key="github_event_backup_import",
        )
        if backup_upload is None:
            st.info(
                "Ein von der App exportiertes Event-ZIP auswählen. "
                "Der Import erzeugt immer ein neues Event mit neuer UUID."
            )
        else:
            backup_bytes = backup_upload.getvalue()
            try:
                inspection = db.inspect_event_backup(backup_bytes)
                source_event = inspection.get("event", {})
                st.success("Gültiges Event-Backup erkannt.")
                st.caption(
                    f"Quelle: {source_event.get('name', '—')} · "
                    f"Dateien: {inspection.get('file_count', 0)} · "
                    f"Berechnungen: {inspection.get('calculation_count', 0)} · "
                    f"Größe: {inspection.get('size_bytes', 0) / (1024 ** 2):.2f} MB"
                )
                import_name = st.text_input(
                    "Name des importierten Events",
                    value=f"{source_event.get('name', 'Importiertes Event')} (Import)",
                    key="github_import_event_name",
                )
                confirm_import = st.checkbox(
                    "Import bestätigen",
                    key="github_confirm_event_import",
                )
                if st.button(
                    "Event jetzt importieren",
                    key="github_import_event_zip",
                    type="primary",
                    disabled=not confirm_import,
                    use_container_width=True,
                ):
                    try:
                        with st.spinner("Event wird importiert …"):
                            imported = db.import_event_zip(
                                backup_bytes,
                                new_name=import_name,
                            )
                        st.session_state.github_database_selected_event = imported["id"]
                        st.session_state.pop("github_repository_statistics", None)
                        refresh_github_repository_statistics(db)
                        st.success(f"Event „{imported['name']}“ wurde importiert.")
                        st.rerun()
                    except GitHubDatabaseError as exc:
                        st.error(f"Import fehlgeschlagen: {exc}")
            except GitHubDatabaseError as exc:
                st.error(str(exc))



def load_analysis_results(
    db,
    event_id: str,
    calculations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    valid = [
        item for item in calculations
        if item.get("_integrity", {}).get("status") == "ok"
    ]
    if len(valid) < 2:
        st.info(
            "Für die Analyse werden mindestens zwei vollständige "
            "gespeicherte Berechnungen benötigt."
        )
        return []

    label_to_id: dict[str, str] = {}
    metadata_by_id: dict[str, dict[str, Any]] = {}
    for item in valid:
        calculation_id = item.get("id")
        label = (
            f"{item.get('name', calculation_id)} · "
            f"{str(item.get('created_at', ''))[:16].replace('T', ' ')}"
        )
        if label in label_to_id:
            label = f"{label} · {calculation_id}"
        label_to_id[label] = calculation_id
        metadata_by_id[calculation_id] = item

    labels = list(label_to_id.keys())
    selected_labels = st.multiselect(
        "Berechnungen vergleichen",
        options=labels,
        default=labels[: min(3, len(labels))],
        key=f"analysis_dashboard_selection_{event_id}",
        help="Mindestens zwei, maximal acht Berechnungen auswählen.",
    )

    if len(selected_labels) < 2:
        st.info("Bitte mindestens zwei Berechnungen auswählen.")
        return []
    if len(selected_labels) > 8:
        st.warning("Es werden maximal acht Berechnungen dargestellt.")
        selected_labels = selected_labels[:8]

    signature = "|".join(label_to_id[label] for label in selected_labels)
    cache_key = f"analysis_dashboard_results_{event_id}"
    signature_key = f"analysis_dashboard_signature_{event_id}"

    if (
        st.session_state.get(signature_key) != signature
        or cache_key not in st.session_state
    ):
        loaded: list[dict[str, Any]] = []
        try:
            with st.spinner("Berechnungen werden geladen …"):
                for label in selected_labels:
                    calculation_id = label_to_id[label]
                    result = db.load_calculation_json(
                        event_id,
                        calculation_id,
                        "result.json",
                    )
                    loaded.append(
                        {
                            "id": calculation_id,
                            "name": metadata_by_id[calculation_id].get(
                                "name",
                                calculation_id,
                            ),
                            "metadata": metadata_by_id[calculation_id],
                            "result": result,
                        }
                    )
            st.session_state[cache_key] = loaded
            st.session_state[signature_key] = signature
        except GitHubDatabaseError as exc:
            st.error(f"Berechnungen konnten nicht geladen werden: {exc}")
            return []

    return st.session_state.get(cache_key, [])


def render_analysis_kpi_cards(
    selected_results: list[dict[str, Any]],
) -> None:
    st.markdown("### Kennzahlen")

    metrics = [
        (
            "Zeit",
            lambda r: format_duration(r.get("duration_s")),
        ),
        (
            "Ø Geschwindigkeit",
            lambda r: (
                "—"
                if _comparison_metric_value(
                    r,
                    "average_speed_kmh",
                    "calibration_speed_kmh",
                ) is None
                else f"{float(_comparison_metric_value(r, 'average_speed_kmh', 'calibration_speed_kmh')):.2f} km/h"
            ),
        ),
        (
            "Average Power",
            lambda r: (
                "—"
                if _comparison_metric_value(
                    r,
                    "average_power_w",
                    "calibration_ap",
                ) is None
                else f"{float(_comparison_metric_value(r, 'average_power_w', 'calibration_ap')):.1f} W"
            ),
        ),
        (
            "Normalized Power",
            lambda r: (
                "—"
                if _comparison_metric_value(
                    r,
                    "normalized_power_w",
                    "calibration_np",
                ) is None
                else f"{float(_comparison_metric_value(r, 'normalized_power_w', 'calibration_np')):.1f} W"
            ),
        ),
        (
            "CdA",
            lambda r: (
                "—"
                if r.get("calibration_cda") is None
                else f"{float(r['calibration_cda']):.5f}"
            ),
        ),
        (
            "Höhenmeter",
            lambda r: (
                "—"
                if r.get("elevation_gain_m") is None
                else f"{float(r['elevation_gain_m']):.0f} m"
            ),
        ),
    ]

    for metric_name, formatter in metrics:
        st.caption(metric_name)
        columns = st.columns(len(selected_results))
        for column, item in zip(columns, selected_results):
            with column:
                st.metric(
                    item["name"],
                    formatter(item["result"]),
                )


def render_analysis_main_chart(
    selected_results: list[dict[str, Any]],
    event_id: str,
) -> None:
    st.markdown("### Verlauf")

    series_name = st.selectbox(
        "Diagramm",
        list(COMPARISON_SERIES.keys()),
        key=f"analysis_dashboard_series_{event_id}",
        label_visibility="collapsed",
    )
    definition = COMPARISON_SERIES[series_name]

    figure = go.Figure()
    x_title = "Strecke [km]"
    trace_count = 0

    for item in selected_results:
        values = _first_series(
            item["result"],
            definition["keys"],
        )
        if values is None:
            continue

        y_values = np.asarray(values, dtype=float)
        x_values, current_x_title = _comparison_distance_axis(
            item["result"],
            len(y_values),
        )
        x_title = current_x_title

        valid = np.isfinite(x_values) & np.isfinite(y_values)
        if not np.any(valid):
            continue

        valid_x = x_values[valid]
        valid_y = y_values[valid]
        if valid_x.size > 3000:
            indices = np.linspace(
                0,
                valid_x.size - 1,
                3000,
            ).astype(int)
            valid_x = valid_x[indices]
            valid_y = valid_y[indices]

        figure.add_trace(
            go.Scatter(
                x=valid_x,
                y=valid_y,
                mode="lines",
                name=item["name"],
                hovertemplate=(
                    "%{x:.2f}<br>%{y:.2f}"
                    "<extra>%{fullData.name}</extra>"
                ),
            )
        )
        trace_count += 1

    if trace_count == 0:
        st.info(
            f"Für „{series_name}“ sind keine vergleichbaren Daten vorhanden."
        )
        return

    figure.update_layout(
        height=620,
        xaxis_title=x_title,
        yaxis_title=definition["y_title"],
        hovermode="x unified",
        legend_title="Berechnung",
        margin=dict(l=20, r=20, t=30, b=20),
    )
    st.plotly_chart(
        figure,
        use_container_width=True,
        key=f"analysis_dashboard_chart_{event_id}_{series_name}",
    )



ANALYSIS_RUN_COLORS = [
    [220, 55, 55, 225],
    [45, 105, 220, 225],
    [35, 165, 85, 225],
    [235, 145, 35, 225],
    [150, 70, 200, 225],
    [20, 165, 175, 225],
    [215, 80, 145, 225],
    [105, 105, 105, 225],
]


def _analysis_metric_values(
    result: dict[str, Any],
    metric_name: str,
) -> list[Any] | None:
    metric_keys = {
        "Berechnung": None,
        "Geschwindigkeit": "map_speed_kmh",
        "Leistung": "map_power_w",
        "Wind": "map_wind_kmh",
        "Windkomponente": "map_wind_component_kmh",
        "Relative Luftgeschwindigkeit": "map_air_speed_kmh",
        "Höhe": "map_elevation_m",
        "Steigung": "map_grade_percent",
    }
    key = metric_keys.get(metric_name)
    if key is None:
        return None
    values = result.get(key)
    return values if isinstance(values, list) else None


def _analysis_metric_unit(metric_name: str) -> str:
    return {
        "Geschwindigkeit": "km/h",
        "Leistung": "W",
        "Wind": "km/h",
        "Windkomponente": "km/h",
        "Relative Luftgeschwindigkeit": "km/h",
        "Höhe": "m",
        "Steigung": "%",
    }.get(metric_name, "")


def render_analysis_comparison_map(
    selected_results: list[dict[str, Any]],
    event_id: str,
) -> None:
    st.markdown("### Kartenvergleich")

    controls = st.columns([2, 1])
    with controls[0]:
        color_mode = st.selectbox(
            "Darstellung",
            [
                "Berechnung",
                "Geschwindigkeit",
                "Leistung",
                "Wind",
                "Windkomponente",
                "Relative Luftgeschwindigkeit",
                "Höhe",
                "Steigung",
            ],
            key=f"analysis_map_mode_{event_id}",
            help=(
                "„Berechnung“ verwendet für jeden Lauf eine feste Farbe. "
                "Die übrigen Modi färben alle Läufe auf einer gemeinsamen Skala ein."
            ),
        )
    with controls[1]:
        line_width = st.slider(
            "Linienbreite",
            min_value=2,
            max_value=12,
            value=6,
            key=f"analysis_map_width_{event_id}",
        )

    visible_names = st.multiselect(
        "Sichtbare Berechnungen",
        [item["name"] for item in selected_results],
        default=[item["name"] for item in selected_results],
        key=f"analysis_map_visible_{event_id}",
    )
    visible_results = [
        item for item in selected_results
        if item["name"] in visible_names
    ]
    if not visible_results:
        st.info("Bitte mindestens eine Berechnung für die Karte auswählen.")
        return

    metric_arrays: list[np.ndarray] = []
    if color_mode != "Berechnung":
        for item in visible_results:
            values = _analysis_metric_values(item["result"], color_mode)
            if values:
                array = np.asarray(values, dtype=float)
                finite = array[np.isfinite(array)]
                if finite.size:
                    metric_arrays.append(finite)

    scale_min = scale_max = None
    if metric_arrays:
        combined = np.concatenate(metric_arrays)
        scale_min = float(np.nanpercentile(combined, 5))
        scale_max = float(np.nanpercentile(combined, 95))
        if not np.isfinite(scale_min) or not np.isfinite(scale_max):
            scale_min = scale_max = None
        elif abs(scale_max - scale_min) < 1e-12:
            scale_max = scale_min + 1.0

    layers = []
    all_latitudes: list[float] = []
    all_longitudes: list[float] = []
    legend_rows = []

    for run_index, item in enumerate(visible_results):
        result = item["result"]
        lat = result.get("map_latitude")
        lon = result.get("map_longitude")
        distance = result.get("map_distance_km")
        if not isinstance(lat, list) or not isinstance(lon, list):
            continue

        n = min(len(lat), len(lon))
        if n < 2:
            continue

        lat_array = np.asarray(lat[:n], dtype=float)
        lon_array = np.asarray(lon[:n], dtype=float)
        valid_coords = np.isfinite(lat_array) & np.isfinite(lon_array)
        if np.count_nonzero(valid_coords) < 2:
            continue

        metric_values = _analysis_metric_values(result, color_mode)
        if metric_values is not None:
            n = min(n, len(metric_values))
            lat_array = lat_array[:n]
            lon_array = lon_array[:n]
            valid_coords = valid_coords[:n]
            metric_array = np.asarray(metric_values[:n], dtype=float)
        else:
            metric_array = np.full(n, np.nan)

        if isinstance(distance, list):
            distance_array = np.asarray(distance[:n], dtype=float)
        else:
            distance_array = np.arange(n, dtype=float)

        segment_data = []
        run_color = ANALYSIS_RUN_COLORS[
            run_index % len(ANALYSIS_RUN_COLORS)
        ]

        for index in range(n - 1):
            if not valid_coords[index] or not valid_coords[index + 1]:
                continue

            if (
                color_mode != "Berechnung"
                and scale_min is not None
                and scale_max is not None
                and np.isfinite(metric_array[index])
            ):
                normalized_value = (
                    float(metric_array[index]) - scale_min
                ) / (scale_max - scale_min)
                color = _color_from_normalized(normalized_value)
                value_text = (
                    f"{float(metric_array[index]):.2f} "
                    f"{_analysis_metric_unit(color_mode)}"
                )
            else:
                color = run_color
                value_text = item["name"]

            segment_data.append(
                {
                    "source": [
                        float(lon_array[index]),
                        float(lat_array[index]),
                    ],
                    "target": [
                        float(lon_array[index + 1]),
                        float(lat_array[index + 1]),
                    ],
                    "color": color,
                    "run": item["name"],
                    "metric": color_mode,
                    "value": value_text,
                    "distance": (
                        f"{float(distance_array[index]):.2f}"
                        if index < len(distance_array)
                        and np.isfinite(distance_array[index])
                        else "—"
                    ),
                }
            )

        if not segment_data:
            continue

        all_latitudes.extend(lat_array[valid_coords].tolist())
        all_longitudes.extend(lon_array[valid_coords].tolist())

        layers.append(
            pdk.Layer(
                "LineLayer",
                data=segment_data,
                get_source_position="source",
                get_target_position="target",
                get_color="color",
                get_width=line_width,
                width_min_pixels=max(2, line_width - 2),
                pickable=True,
            )
        )
        legend_rows.append((item["name"], run_color))

    if not layers or not all_latitudes or not all_longitudes:
        st.info("Für die ausgewählten Berechnungen sind keine GPS-Daten verfügbar.")
        return

    lat_span = max(all_latitudes) - min(all_latitudes)
    lon_span = max(all_longitudes) - min(all_longitudes)
    span = max(lat_span, lon_span)
    if span < 0.01:
        zoom = 13
    elif span < 0.03:
        zoom = 11
    elif span < 0.08:
        zoom = 10
    elif span < 0.2:
        zoom = 9
    elif span < 0.5:
        zoom = 8
    else:
        zoom = 7

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=float(np.nanmean(all_latitudes)),
            longitude=float(np.nanmean(all_longitudes)),
            zoom=zoom,
            pitch=0,
        ),
        map_style=None,
        tooltip={
            "html": (
                "<b>{run}</b><br/>"
                "{metric}: {value}<br/>"
                "Distanz: {distance} km"
            ),
            "style": {
                "backgroundColor": "rgba(20,20,20,0.92)",
                "color": "white",
                "fontSize": "0.85rem",
            },
        },
    )
    st.pydeck_chart(
        deck,
        use_container_width=True,
        height=650,
    )

    if color_mode == "Berechnung":
        legend_html = " ".join(
            (
                "<span style='display:inline-flex;align-items:center;"
                "margin-right:18px;margin-bottom:8px;'>"
                f"<span style='width:14px;height:14px;border-radius:50%;"
                f"background:rgba({color[0]},{color[1]},{color[2]},0.9);"
                "display:inline-block;margin-right:6px;'></span>"
                f"{name}</span>"
            )
            for name, color in legend_rows
        )
        st.markdown(legend_html, unsafe_allow_html=True)
    elif scale_min is not None and scale_max is not None:
        unit = _analysis_metric_unit(color_mode)
        st.markdown(
            f"""
            <div style="margin-top:0.5rem;margin-bottom:0.75rem;">
                <div style="
                    height:18px;border-radius:9px;
                    background:linear-gradient(
                        90deg,
                        rgb(30,90,220) 0%,
                        rgb(50,230,140) 33%,
                        rgb(250,210,40) 66%,
                        rgb(250,50,20) 100%
                    );
                    border:1px solid rgba(0,0,0,0.25);
                "></div>
                <div style="display:flex;justify-content:space-between;">
                    <span>{scale_min:.2f} {unit}</span>
                    <span>{scale_max:.2f} {unit}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_analysis_differences(
    selected_results: list[dict[str, Any]],
    event_id: str,
) -> None:
    st.markdown("### Differenzen zur Referenz")

    names = [item["name"] for item in selected_results]
    reference_name = st.selectbox(
        "Referenz",
        names,
        key=f"analysis_dashboard_reference_{event_id}",
    )
    reference = next(
        item for item in selected_results
        if item["name"] == reference_name
    )
    reference_result = reference["result"]

    rows = []
    for item in selected_results:
        result = item["result"]

        def delta(*keys: str) -> float | None:
            current = _comparison_metric_value(result, *keys)
            reference_value = _comparison_metric_value(
                reference_result,
                *keys,
            )
            if current is None or reference_value is None:
                return None
            return float(current) - float(reference_value)

        rows.append(
            {
                "Berechnung": item["name"],
                "Δ Zeit [s]": delta("duration_s"),
                "Δ Geschwindigkeit [km/h]": delta(
                    "average_speed_kmh",
                    "calibration_speed_kmh",
                ),
                "Δ AP [W]": delta(
                    "average_power_w",
                    "calibration_ap",
                ),
                "Δ NP [W]": delta(
                    "normalized_power_w",
                    "calibration_np",
                ),
                "Δ CdA": delta("calibration_cda"),
            }
        )

    difference_df = pd.DataFrame(rows)
    st.dataframe(
        difference_df,
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "Differenzen als CSV herunterladen",
        data=difference_df.to_csv(index=False).encode("utf-8"),
        file_name="analyse_differenzen.csv",
        mime="text/csv",
        use_container_width=True,
    )


def render_saved_calculation_analysis() -> None:
    st.caption("Vergleich gespeicherter Berechnungen aus der GitHub-Datenbank.")

    db = get_github_database()
    if db is None:
        st.warning(
            "Die GitHub-Datenbank ist nicht konfiguriert. "
            "Bitte zuerst den Bereich „Datenbank“ einrichten."
        )
        return

    try:
        events = db.list_events()
    except GitHubDatabaseError as exc:
        st.error(f"Events konnten nicht geladen werden: {exc}")
        return

    if not events:
        st.info("In der GitHub-Datenbank sind noch keine Events vorhanden.")
        return

    event_labels: dict[str, str] = {}
    for event in events:
        base_label = (
            f"{event.get('name', event.get('id'))} · "
            f"{event.get('date') or 'ohne Datum'}"
        )
        label = base_label
        if label in event_labels:
            label = f"{base_label} · {event.get('id')}"
        event_labels[label] = event.get("id")

    current_event_id = st.session_state.get(
        "github_database_selected_event"
    )
    labels = list(event_labels.keys())
    default_index = 0
    if current_event_id:
        for index, label in enumerate(labels):
            if event_labels[label] == current_event_id:
                default_index = index
                break

    selected_event_label = st.selectbox(
        "Event",
        labels,
        index=default_index,
        key="analysis_event_selection",
    )
    event_id = event_labels[selected_event_label]
    st.session_state.github_database_selected_event = event_id

    try:
        event = db.load_event(event_id)
        calculations = db.list_calculations(event_id)
    except GitHubDatabaseError as exc:
        st.error(f"Analysedaten konnten nicht geladen werden: {exc}")
        return

    header_cols = st.columns(4)
    header_cols[0].metric("Event", event.get("name", event_id))
    header_cols[1].metric("Berechnungen", len(calculations))
    header_cols[2].metric(
        "Vollständig",
        sum(
            1 for item in calculations
            if item.get("_integrity", {}).get("status") == "ok"
        ),
    )
    header_cols[3].metric(
        "Beschädigt",
        sum(
            1 for item in calculations
            if item.get("_integrity", {}).get("status") != "ok"
        ),
    )

    st.divider()
    selected_results = load_analysis_results(
        db,
        event_id,
        calculations,
    )
    if len(selected_results) < 2:
        return

    render_analysis_kpi_cards(selected_results)
    st.divider()
    render_analysis_main_chart(selected_results, event_id)
    st.divider()
    render_analysis_comparison_map(selected_results, event_id)
    st.divider()
    render_analysis_differences(selected_results, event_id)

    with st.expander("Vollständige Vergleichstabelle", expanded=False):
        summary_df = build_comparison_summary(selected_results)
        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "Vergleichstabelle als CSV herunterladen",
            data=summary_df.to_csv(index=False).encode("utf-8"),
            file_name="berechnungsvergleich.csv",
            mime="text/csv",
            use_container_width=True,
        )



def render_analysis_area() -> None:
    st.title("📊 Analyse")
    analysis_mode = st.radio(
        "Analyseart",
        ["Berechnungsvergleich", "Parameterstudie"],
        horizontal=True,
        key="analysis_mode",
    )
    st.divider()
    if analysis_mode == "Parameterstudie":
        render_parameter_study()
    else:
        render_saved_calculation_analysis()


def main() -> None:
    init_session_state()
    apply_pending_navigation()

    with st.sidebar:
        st.header("Navigation")
        app_area = st.radio(
            "Bereich",
            ["🚴 Rechner", "📊 Analyse", "🗄 Datenbank"],
            key="app_main_area",
            label_visibility="collapsed",
        )
        st.caption(f"Version {APP_VERSION} · Build {BUILD_DATE}")

    if app_area == "📊 Analyse":
        render_analysis_area()
        return

    if app_area == "🗄 Datenbank":
        st.title("🗄 GitHub-Datenbank")
        st.caption(
            "Events, Dateien, gespeicherte Berechnungen und Backups verwalten."
        )
        render_github_database_sidebar()
        return

    apply_pending_loaded_config_on_calculator()

    flash_message = st.session_state.pop("database_load_message", None)
    if flash_message:
        st.success(flash_message)

    st.title("🚴 Bike Power Calculator")
    st.caption(
        f"Version {APP_VERSION} – stabiler Rechenkern mit optionalem Entwicklermodus"
    )

    with st.sidebar:
        st.divider()
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
                    queue_loaded_config(loaded_config)
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

    # Datei-Uploads bleiben sofort wirksam. Die übrigen Rechnerwerte werden
    # dagegen gesammelt und erst beim Absenden des Formulars übernommen.
    if route_path:
        st.session_state.config["GPX/FIT Datei"] = route_path
    if weather_path:
        st.session_state.config["Wetterdatei Advanced Weather"] = weather_path

    # Fragment-Eingabe: Änderungen der Zahlenfelder aktualisieren nur diesen
    # kleinen Bereich. Dadurch funktionieren die +/- Bedienelemente sichtbar,
    # ohne dass Ergebnisse, Karten und Diagramme vollständig neu aufgebaut werden.
    @st.fragment
    def render_calculator_settings_fragment() -> None:
        fragment_config = st.session_state.config.copy()

        tab_keys = ["basis", "aero", "leistung", "wetter", "strecke", "ausgabe"]
        tabs = st.tabs([GROUP_TITLES[key] for key in tab_keys])

        updated: dict[str, Any] = {}
        for tab, group_key in zip(tabs, tab_keys):
            with tab:
                updated.update(render_group(group_key, fragment_config))

        if route_path:
            updated["GPX/FIT Datei"] = route_path
        elif fragment_config.get("GPX/FIT Datei"):
            updated["GPX/FIT Datei"] = fragment_config.get("GPX/FIT Datei")

        if weather_path:
            updated["Wetterdatei Advanced Weather"] = weather_path
        elif fragment_config.get("Wetterdatei Advanced Weather"):
            updated["Wetterdatei Advanced Weather"] = fragment_config.get(
                "Wetterdatei Advanced Weather"
            )

        st.divider()
        st.subheader("Ausgabe")
        out_col1, out_col2 = st.columns(2)
        with out_col1:
            generate_pdf_value = st.checkbox(
                "PDF erzeugen",
                value=st.session_state.generate_pdf,
                help=(
                    "Ausschalten spart typischerweise mehrere Sekunden. "
                    "Download und PDF-Vorschau entfallen dann."
                ),
                key="calculator_fragment_generate_pdf",
            )
        with out_col2:
            generate_html_value = st.checkbox(
                "HTML-Karte erzeugen",
                value=st.session_state.generate_html_map,
                help=(
                    "Ausschalten spart etwas Zeit. "
                    "Die interaktiven Diagramme bleiben erhalten."
                ),
                key="calculator_fragment_generate_html",
            )

        weather_mode = str(
            updated.get(
                "Verwendung Advanced Weather",
                fragment_config.get("Verwendung Advanced Weather", ""),
            )
        )
        if weather_mode.startswith("True,True"):
            refresh_weather_value = st.checkbox(
                "Online-Wetter neu laden",
                value=False,
                help=(
                    "Löscht vor dieser Berechnung den lokalen Open-Meteo-Cache. "
                    "Ohne Haken werden identische Abfragen bis zu 30 Tage "
                    "wiederverwendet."
                ),
                key="calculator_fragment_refresh_weather",
            )
        else:
            refresh_weather_value = False

        # Der Fragment-Rerun ist klein und schnell; die Konfiguration darf daher
        # bei jeder sichtbaren Änderung direkt synchronisiert werden.
        st.session_state.config = normalize_loaded_config(updated)
        st.session_state.generate_pdf = bool(generate_pdf_value)
        st.session_state.generate_html_map = bool(generate_html_value)
        st.session_state.refresh_weather_cache = bool(refresh_weather_value)

        optimization_active = _optimization_is_active(
            st.session_state.config
        )
        if optimization_active:
            st.markdown("#### Pacing-Optimierung")
            st.caption(
                "Die zusätzlichen Einstellungen erscheinen nur, weil ein "
                "positiver NP-Sollwert und mindestens zwei unterschiedliche "
                "Maximalleistungen vorgegeben sind."
            )
            fine_enabled = st.checkbox(
                "Optimum automatisch fein eingrenzen",
                value=bool(
                    st.session_state.get(
                        "optimization_fine_enabled",
                        False,
                    )
                ),
                key="optimization_fine_enabled_widget",
            )
            fine_cols = st.columns(2)
            with fine_cols[0]:
                fine_radius = st.number_input(
                    "Feinbereich ± [W]",
                    min_value=1.0,
                    value=float(
                        st.session_state.get(
                            "optimization_fine_radius_w",
                            10.0,
                        )
                    ),
                    step=1.0,
                    disabled=not fine_enabled,
                    key="optimization_fine_radius_widget",
                )
            with fine_cols[1]:
                fine_step = st.number_input(
                    "Feinschritt [W]",
                    min_value=0.5,
                    value=float(
                        st.session_state.get(
                            "optimization_fine_step_w",
                            1.0,
                        )
                    ),
                    step=0.5,
                    disabled=not fine_enabled,
                    key="optimization_fine_step_widget",
                )
            st.session_state.optimization_fine_enabled = bool(fine_enabled)
            st.session_state.optimization_fine_radius_w = float(fine_radius)
            st.session_state.optimization_fine_step_w = float(fine_step)
        else:
            st.session_state.optimization_fine_enabled = False

        st.caption(
            "Änderungen werden sofort übernommen. Dabei wird nur der "
            "Eingabebereich aktualisiert, nicht die komplette Seite."
        )

        apply_col, run_col = st.columns(2)
        with apply_col:
            if st.button(
                "Einstellungen übernommen",
                use_container_width=True,
                key="calculator_fragment_apply",
            ):
                st.success("Einstellungen sind aktuell.")
        with run_col:
            if st.button(
                "Berechnung starten",
                type="primary",
                use_container_width=True,
                key="calculator_fragment_start",
            ):
                st.session_state.pending_calculation_start = True
                st.rerun(scope="app")

        if st.session_state.generate_pdf or st.session_state.generate_html_map:
            st.info(
                "Die Berechnung erzeugt die ausgewählten Ausgaben. "
                "Für schnelle Tests kannst du PDF/Karte deaktivieren."
            )
        else:
            st.info(
                "Schnellmodus aktiv: Es werden nur Berechnung und "
                "interaktive Diagramme erzeugt."
            )

    render_calculator_settings_fragment()
    start_clicked = bool(
        st.session_state.pop("pending_calculation_start", False)
    )

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
                        coarse_power_values = _parse_max_power_values(
                            run_config.get(
                                "max. Leistung (Liste( [W]",
                                "",
                            )
                        )
                        fine_requested = bool(
                            st.session_state.get(
                                "optimization_fine_enabled",
                                False,
                            )
                            and _optimization_is_active(run_config)
                        )

                        result = run_single_simulation(
                            run_config,
                            generate_pdf=(
                                st.session_state.generate_pdf
                                and not fine_requested
                            ),
                            generate_html_map=(
                                st.session_state.generate_html_map
                                and not fine_requested
                            ),
                        )
                        if isinstance(result, dict):
                            result["optimization_coarse_power_values"] = (
                                coarse_power_values
                            )
                            result["optimization_fine_requested"] = (
                                fine_requested
                            )
                            result["optimization_fine_applied"] = False

                        if fine_requested and len(coarse_power_values) >= 3:
                            coarse_best = _best_optimization_row(result)
                            if coarse_best is not None:
                                best_power = float(
                                    coarse_best["max_power_w"]
                                )
                                at_boundary = (
                                    best_power == min(coarse_power_values)
                                    or best_power == max(coarse_power_values)
                                )
                                if isinstance(result, dict):
                                    result[
                                        "optimization_best_at_coarse_boundary"
                                    ] = at_boundary

                                if not at_boundary:
                                    fine_values = _fine_power_values(
                                        best_power,
                                        float(
                                            st.session_state.get(
                                                "optimization_fine_radius_w",
                                                10.0,
                                            )
                                        ),
                                        float(
                                            st.session_state.get(
                                                "optimization_fine_step_w",
                                                1.0,
                                            )
                                        ),
                                    )
                                    combined_values = sorted(
                                        set(
                                            coarse_power_values
                                            + fine_values
                                        )
                                    )
                                    fine_config = dict(run_config)
                                    fine_config[
                                        "max. Leistung (Liste( [W]"
                                    ] = _format_power_list(
                                        combined_values
                                    )
                                    result = run_single_simulation(
                                        fine_config,
                                        generate_pdf=(
                                            st.session_state.generate_pdf
                                        ),
                                        generate_html_map=(
                                            st.session_state.generate_html_map
                                        ),
                                    )
                                    if isinstance(result, dict):
                                        result[
                                            "optimization_coarse_power_values"
                                        ] = coarse_power_values
                                        result[
                                            "optimization_fine_power_values"
                                        ] = fine_values
                                        result[
                                            "optimization_fine_requested"
                                        ] = True
                                        result[
                                            "optimization_fine_applied"
                                        ] = True
                                        result[
                                            "optimization_best_at_coarse_boundary"
                                        ] = False
                        elif fine_requested and isinstance(result, dict):
                            result[
                                "optimization_fine_note"
                            ] = (
                                "Für die automatische Feinoptimierung sind "
                                "mindestens drei grobe Maximalleistungswerte "
                                "erforderlich."
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
