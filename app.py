
import streamlit as st
import json

st.set_page_config(page_title="Bike Power Calculator", layout="wide")

st.title("🚴 Bike Power Calculator")

st.sidebar.header("Projektstatus")
st.sidebar.success("Version 0.1")

DEFAULTS = {
    "Titel":"Default",
    "FTP":244,
    "Gewicht Fahrer":74.0,
    "Gewicht Bike":10.0,
    "Rollwiderstand":0.003,
    "CdA flach":0.265,
    "CdA Berg":0.33,
    "NP Soll":207,
}

st.header("Fahrer & Rad")
c1,c2=st.columns(2)
with c1:
    title=st.text_input("Titel",DEFAULTS["Titel"])
    ftp=st.number_input("FTP [W]",value=DEFAULTS["FTP"])
    rider=st.number_input("Gewicht Fahrer [kg]",value=DEFAULTS["Gewicht Fahrer"])
with c2:
    bike=st.number_input("Gewicht Bike [kg]",value=DEFAULTS["Gewicht Bike"])
    cr=st.number_input("Rollwiderstand",value=DEFAULTS["Rollwiderstand"],format="%.4f")
    nps=st.number_input("NP Soll [W]",value=DEFAULTS["NP Soll"])

st.header("Dateien")
gpx=st.file_uploader("GPX/FIT",type=["gpx","fit"])
weather=st.file_uploader("Wetter CSV",type=["csv"])
settings=st.file_uploader("JSON Einstellungen",type=["json"])

if settings:
    cfg=json.load(settings)
    st.json(cfg)

if st.button("Berechnung starten",type="primary"):
    st.info("Die Berechnungslogik wird im nächsten Entwicklungsschritt angebunden.")
    st.write({
        "Titel":title,
        "FTP":ftp,
        "Gewicht Fahrer":rider,
        "Gewicht Bike":bike,
        "Rollwiderstand":cr,
        "NP":nps,
        "GPX":None if gpx is None else gpx.name,
        "Weather":None if weather is None else weather.name
    })
