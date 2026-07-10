from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from plots import render_interactive_charts
from profiling import render_internal_profiles, render_profile


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def pdf_viewer(pdf_path: Path, max_pages: int = 12) -> None:
    try:
        import fitz
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

    render_profile(profile)

    st.subheader("Ergebnisse")

    distance = result.get("distance_km")
    duration = result.get("duration_s")
    avg_speed = result.get("average_speed_kmh")

    metric_cols = st.columns(4)
    metric_cols[0].metric("Titel", result.get("title", "—"))
    metric_cols[1].metric("Distanz", "—" if distance is None else f"{distance:.2f} km")
    metric_cols[2].metric("Zeit", format_duration(duration))
    metric_cols[3].metric("Ø Geschwindigkeit", "—" if avg_speed is None else f"{avg_speed:.2f} km/h")

    render_internal_profiles(result)

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
            st.info("Keine PDF-Datei erzeugt.")

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
            st.info("Keine HTML-Karte erzeugt.")

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
