from __future__ import annotations

import contextlib
import io
import time
import traceback

import streamlit as st

from calc_adapter import call_bike_power_calc
from exports import render_results
from ui import (
    init_session_state,
    normalize_loaded_config,
    render_file_uploads,
    render_output_options,
    render_parameter_tabs,
    render_run_controls,
    render_sidebar,
    resolve_repository_path,
)


st.set_page_config(
    page_title="Bike Power Calculator",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    init_session_state()

    st.title("🚴 Bike Power Calculator")
    st.caption("Streamlit-Migration der bestehenden Desktop-App – Version 1.7")

    st.markdown(
        """
        <style>
        .stMetric { border: 1px solid rgba(49, 51, 63, 0.15); border-radius: 0.75rem; padding: 0.75rem; }
        div[data-testid="stExpander"] { border-radius: 0.75rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    render_sidebar()

    config = st.session_state.config.copy()
    config = render_file_uploads(config)
    config = render_parameter_tabs(config)
    st.session_state.config = normalize_loaded_config(config)

    render_output_options()
    start_clicked = render_run_controls()

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
                        progress.progress(25, text="Strecke, Wetter und Ausgaben werden berechnet …")
                        t_calc_start = time.perf_counter()
                        result = call_bike_power_calc(
                            run_config,
                            st.session_state.generate_pdf,
                            st.session_state.generate_html_map,
                        )
                        profile["calculation_s"] = time.perf_counter() - t_calc_start

                    t_post_start = time.perf_counter()
                    progress.progress(100, text="Berechnung abgeschlossen.")
                    st.session_state.result = result
                    st.session_state.run_log = log_buffer.getvalue()
                    profile["postprocess_s"] = time.perf_counter() - t_post_start

                profile["total_s"] = time.perf_counter() - t_total_start
                profile["other_s"] = max(
                    0.0,
                    profile["total_s"]
                    - profile.get("validation_s", 0.0)
                    - profile.get("calculation_s", 0.0)
                    - profile.get("postprocess_s", 0.0),
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

    with st.expander("Aktuelle Konfiguration anzeigen"):
        st.json(st.session_state.config)


if __name__ == "__main__":
    main()
