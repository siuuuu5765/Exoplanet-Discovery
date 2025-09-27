import pandas as pd
from astroquery.nasa_exoplanet_archive import NasaExoplanetArchive
from lightkurve import search_lightcurve

# Habitability scoring
def habitability_score(radius, period, stellar_mag):
    score = 0
    if 0.5 <= radius <= 2: score += 40
    elif 0.2 <= radius < 0.5 or 2 < radius <= 4: score += 20
    if 50 <= period <= 400: score += 40
    elif 20 <= period < 50 or 400 < period <= 600: score += 20
    score += max(0, 20 - stellar_mag)
    return min(100, score)

# Fetch planet data
def fetch_planet_data(tic_id):
    try:
        table = NasaExoplanetArchive.query_criteria(
            table="ps",
            select="pl_name,pl_rade,pl_orbper,st_optmag,pl_discmethod",
            where=f"hostname like '%{tic_id}%'",
        )
        if len(table) == 0: return None
        planet = table[0]
        radius = float(planet['pl_rade']) if planet['pl_rade'] else 1.0
        period = float(planet['pl_orbper']) if planet['pl_orbper'] else 365
        mag = float(planet['st_optmag']) if planet['st_optmag'] else 10
        score = habitability_score(radius, period, mag)
        return {
            "name": planet['pl_name'],
            "radius": radius,
            "orbital_period": period,
            "stellar_mag": mag,
            "type": "Unknown",
            "discovery_method": planet['pl_discmethod'],
            "habitability_score": score
        }
    except:
        return None

# Fetch lightcurve
def fetch_lightcurve(tic_id):
    try:
        lc_search = search_lightcurve(f"TIC {tic_id}", mission="TESS")
        if len(lc_search) == 0: return None
        lc = lc_search[0].download()
        return lc.time.value, lc.flux.value
    except:
        return None
