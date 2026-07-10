from __future__ import annotations

import pandas as pd
import streamlit as st


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


def render_internal_profiles(result: dict) -> None:
    steps = result.get("profile_steps")
    if isinstance(steps, list) and steps:
        with st.expander("Detail-Profil der Berechnung", expanded=True):
            df_steps = pd.DataFrame(steps)
            if "Zeit [s]" in df_steps.columns:
                df_steps["Zeit [s]"] = df_steps["Zeit [s]"].astype(float)
                st.bar_chart(df_steps.set_index("Abschnitt")["Zeit [s]"])
            st.dataframe(df_steps, use_container_width=True, hide_index=True)

    detailed_steps = result.get("detailed_profile_steps")
    if isinstance(detailed_steps, list) and detailed_steps:
        with st.expander("Feinprofil bike_power_main_calc()", expanded=True):
            df_detail = pd.DataFrame(detailed_steps)
            if "Zeit [s]" in df_detail.columns:
                df_detail["Zeit [s]"] = df_detail["Zeit [s]"].astype(float)
                df_sum = df_detail.groupby("Abschnitt", as_index=False)["Zeit [s]"].sum()
                st.bar_chart(df_sum.set_index("Abschnitt")["Zeit [s]"])
                st.dataframe(df_sum, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_detail, use_container_width=True, hide_index=True)
