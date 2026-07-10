from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


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
    fig1.update_layout(title="Höhenprofil und Steigung", xaxis_title=x_label, yaxis_title="Wert", hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = go.Figure()
    add_line(fig2, result, x, "Leistung [W]", "power")
    add_line(fig2, result, x, "FIT-Leistung [W]", "Power_fit")
    fig2.update_layout(title="Leistung", xaxis_title=x_label, yaxis_title="Leistung [W]", hovermode="x unified")
    if fig2.data:
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Keine Leistungsdaten gefunden.")

    fig3 = go.Figure()
    add_line(fig3, result, x, "Geschwindigkeit [km/h]", "v")
    add_line(fig3, result, x, "Wind effektiv [km/h]", "v_w_List")
    fig3.update_layout(title="Geschwindigkeit und Wind", xaxis_title=x_label, yaxis_title="km/h", hovermode="x unified")
    st.plotly_chart(fig3, use_container_width=True)

    fig4 = go.Figure()
    add_line(fig4, result, x, "CdA [m²]", "cdA_List")
    add_line(fig4, result, x, "Luftdichte [kg/m³]", "rho_List")
    fig4.update_layout(title="Aerodynamik und Luftdichte", xaxis_title=x_label, yaxis_title="Wert", hovermode="x unified")
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
        fig5.update_layout(title="Advanced Weather", xaxis_title=x_label, yaxis_title="Wert", hovermode="x unified")
        st.plotly_chart(fig5, use_container_width=True)

    with st.expander("Interaktive Rohdaten anzeigen"):
        data = {"x": x}
        for key in [
            "h", "h_raw", "grade", "power", "Power_fit", "v", "v_w_List",
            "rho_List", "cdA_List", "P_r_rel", "P_g_rel", "P_l_rel", "P_ges", "P_Save",
            "AdvWeather_TempC", "AdvWeather_AirSpeed", "AdvWeather_AirDir",
            "AdvWeather_AirMoisture", "AdvWeather_AirPressure",
        ]:
            series = result.get(key)
            if isinstance(series, list) and series:
                _, yy = same_length(x, series)
                data[key] = yy
        max_len = min(len(v) for v in data.values() if isinstance(v, list))
        data = {k: v[:max_len] if isinstance(v, list) else v for k, v in data.items()}
        st.dataframe(pd.DataFrame(data), use_container_width=True)
