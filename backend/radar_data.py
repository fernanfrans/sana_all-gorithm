import numpy as np
import streamlit as st

@st.cache_data
def generate_radar_data():
    lat_range = np.linspace(10, 20, 50)
    lon_range = np.linspace(118, 128, 50)
    lon_grid, lat_grid = np.meshgrid(lon_range, lat_range)

    center_lat, center_lon = 14.5, 121.0
    distance = np.sqrt((lat_grid - center_lat)**2 + (lon_grid - center_lon)**2)
    angle = np.arctan2(lat_grid - center_lat, lon_grid - center_lon)
    spiral = np.sin(3 * angle + 2 * distance)

    rainfall = 50 * np.exp(-distance/2) * (1 + 0.5 * spiral) * np.random.uniform(0.8, 1.2, distance.shape)
    return lat_grid, lon_grid, np.maximum(rainfall, 0)
