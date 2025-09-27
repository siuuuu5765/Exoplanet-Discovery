# app.py
import streamlit as st
import pandas as pd
import numpy as np
from astroquery.nasa_exoplanet_archive import NasaExoplanetArchive
from lightkurve import search_lightcurve
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(page_title="ExoPlanet Discovery Hub", layout="wide")
st.title("🌌 ExoPlanet Discovery Hub – Real TESS Data")

# ------------------------------
# Helper: Habitability Scoring
# ------------------------------
def habitability_score(radius, period, stellar_mag):
    score = 0
    # Radius scoring
    if 0.5 <= radius <= 2: score += 40
    elif 0.2 <= radius < 0.5 or 2 < radius <= 4: score += 20
    # Period scoring (simple HZ approximation)
    if 50 <= period <= 400: score += 40
    elif 20 <= period < 50 or 400 < period <= 600: score += 20
    # Stellar brightness (lower magnitude = brighter)
    score += max(0, 20 - stellar_mag)
    return min(100, score)

# ------------------------------
# Fetch Planet Data
# ------------------------------
@st.cache_data
def fetch_planet_data(tic_id):
    try:
        table = NasaExoplanetArchive.query_criteria(
            table="ps",
            select="pl_name,pl_rade,pl_orbper,st_optmag,pl_discmethod",
            where=f"hostname like '%{tic_id}%'",
        )
        if len(table) == 0:
            return None
        planet = table[0]
        radius = float(planet['pl_rade']) if planet['pl_rade'] else 1.0
        period = float(planet['pl_orbper']) if planet['pl_orbper'] else 365
        mag = float(planet['st_optmag']) if planet['st_optmag'] else 10
        planet_type = "Unknown"
        score = habitability_score(radius, period, mag)
        return {
            "name": planet['pl_name'],
            "radius": radius,
            "orbital_period": period,
            "stellar_mag": mag,
            "type": planet_type,
            "discovery_method": planet['pl_discmethod'],
            "habitability_score": score
        }
    except:
        return None

# ------------------------------
# Fetch Light Curve
# ------------------------------
@st.cache_data
def fetch_lightcurve(tic_id):
    try:
        lc_search = search_lightcurve(f"TIC {tic_id}", mission="TESS")
        if len(lc_search) == 0:
            return None
        lc = lc_search[0].download()
        return lc.time.value, lc.flux.value
    except:
        return None

# ------------------------------
# Sidebar – TIC Input & Top Planets
# ------------------------------
tic_id = st.sidebar.text_input("Enter TIC ID:", "")
top_n = st.sidebar.slider("Top N Habitable Planets to Compare:", 2, 10, 5)

st.sidebar.markdown("## 💡 Extra Features")
st.sidebar.markdown("- 3D Orbit Visualization")
st.sidebar.markdown("- AI Assistant explains planet properties")
st.sidebar.markdown("- Export planet report as PDF")

# ------------------------------
# Main Section
# ------------------------------
if tic_id:
    planet = fetch_planet_data(tic_id)
    if planet is None:
        st.warning("No planet data found for this TIC ID.")
    else:
        # ------------------------------
        # Planet Info
        # ------------------------------
        st.subheader(f"Planet Analysis: {planet['name']}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Radius (R⊕)", planet['radius'])
        col2.metric("Orbital Period (days)", planet['orbital_period'])
        col3.metric("Stellar Magnitude", planet['stellar_mag'])
        st.write(f"**Discovery Method:** {planet['discovery_method']}")
        st.write(f"**Habitability Score:** {planet['habitability_score']}/100 🌱")

        # ------------------------------
        # Light Curve
        # ------------------------------
        lc_data = fetch_lightcurve(tic_id)
        if lc_data:
            time, flux = lc_data
            fig, ax = plt.subplots(figsize=(10,3))
            ax.plot(time, flux, color='indigo')
            ax.set_xlabel("Time (days)")
            ax.set_ylabel("Normalized Flux")
            ax.set_title("Transit Light Curve")
            st.pyplot(fig)
        else:
            st.info("No light curve available for this TIC ID.")

        # ------------------------------
        # AI Assistant
        # ------------------------------
        st.markdown("### 🤖 AI Assistant")
        ai_input = st.text_input("Ask about this planet:", "")
        if ai_input:
            msg = ai_input.lower()
            if "radius" in msg:
                response = f"Radius: {planet['radius']} R⊕ (~{planet['radius']} Earth radii)"
            elif "period" in msg or "orbit" in msg:
                response = f"Orbital period: {planet['orbital_period']} days"
            elif "habitability" in msg:
                response = f"Habitability Index: {planet['habitability_score']}/100 🌱"
            elif "discovery" in msg:
                response = f"Discovered using {planet['discovery_method']}."
            elif "magnitude" in msg or "brightness" in msg:
                response = f"Star brightness: {planet['stellar_mag']} magnitude"
            else:
                response = "You can ask about radius, orbital period, habitability, brightness, or discovery method."
            st.info(response)

        # ------------------------------
        # Top N Habitable Planets
        # ------------------------------
        st.markdown(f"### 🌟 Top {top_n} Habitable Planets (Sample from TESS)")
        df = NasaExoplanetArchive.query_criteria(
            table="ps",
            select="pl_name,pl_rade,pl_orbper,st_optmag,pl_discmethod",
        ).to_pandas()
        df = df.dropna(subset=['pl_rade','pl_orbper','st_optmag']).copy()
        df['habitability'] = df.apply(lambda row: habitability_score(row['pl_rade'], row['pl_orbper'], row['st_optmag']), axis=1)
        top_planets = df.sort_values('habitability', ascending=False).head(top_n)
        st.dataframe(top_planets[['pl_name','pl_rade','pl_orbper','st_optmag','habitability']])

        # ------------------------------
        # 3D Orbit Visualization
        # ------------------------------
        st.markdown("### 🪐 3D Orbit Visualization (Simplified)")
        fig3d = go.Figure()
        fig3d.add_trace(go.Scatter3d(x=[0, planet['orbital_period']], y=[0, planet['radius']], z=[0,0],
                                     mode='lines+markers', line=dict(color='indigo', width=4)))
        fig3d.update_layout(scene=dict(
            xaxis_title='Orbital Period (days)',
            yaxis_title='Radius (R⊕)',
            zaxis_title='Z (AU)'
        ))
        st.plotly_chart(fig3d)

        # ------------------------------
        # Export Report
        # ------------------------------
        st.markdown("### 📝 Export Planet Report")
        if st.button("Download PDF Report"):
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, f"ExoPlanet Report: {planet['name']}", ln=True)
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 10, f"Radius: {planet['radius']} R⊕", ln=True)
            pdf.cell(0, 10, f"Orbital Period: {planet['orbital_period']} days", ln=True)
            pdf.cell(0, 10, f"Stellar Magnitude: {planet['stellar_mag']}", ln=True)
            pdf.cell(0, 10, f"Discovery Method: {planet['discovery_method']}", ln=True)
            pdf.cell(0, 10, f"Habitability Score: {planet['habitability_score']}/100", ln=True)
            pdf_output = BytesIO()
            pdf.output(pdf_output)
            st.download_button("Download PDF", pdf_output.getvalue(), file_name=f"{planet['name']}_report.pdf")
