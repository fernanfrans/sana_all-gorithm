import numpy as np
import streamlit as st
import folium
import time
from streamlit_folium import st_folium
from backend.radar_data import generate_radar_data
from folium.plugins import HeatMap
from folium import FeatureGroup, Marker

def render_radar():
    st.markdown("### 🎯 Weather Radar - Real-time Precipitation")

    # Heatmap gradient based on reflectivity value
    GRADIENT = {
        0.00: 'rgba(0,0,0,0)',     # transparent (no rain)
        0.05: '#001040',           # very light drizzle – dark navy
        0.10: '#0020A0',           # light rain – blue
        0.20: '#0040FF',           # light-moderate rain – bright blue
        0.30: '#00A0FF',           # moderate rain – cyan
        0.40: '#00FFC0',           # moderate-heavy rain – aqua green
        0.50: '#00FF00',           # heavy rain – green
        0.60: '#A0FF00',           # very heavy rain – lime
        0.70: '#FFFF00',           # intense rain – yellow
        0.80: '#FFA000',           # extreme rain – orange
        0.90: '#FF4000',           # torrential – red-orange
        1.00: '#FF0000'            # max reflectivity – bright red
    }

    # Set up initial values for helper variables
    map_container = st.container()
    frames = list(range(5, 120, 5))

    # Set up initial values for cached variables
    if "frame_idx" not in st.session_state:
        st.session_state.frame_idx = 0

    if "map_center" not in st.session_state or "map_bounds" not in st.session_state:
        # Get initial latitude and longitude grids
        lat_grid_0, lon_grid_0, _ = generate_radar_data(f"prediction_+{frames[0]}min.json")

        # Set map center
        st.session_state.map_center = [np.mean(lat_grid_0), np.mean(lon_grid_0)]

        # Also set map bounds
        min_lat, max_lat = np.min(lat_grid_0), np.max(lat_grid_0)
        min_lon, max_lon = np.min(lon_grid_0), np.max(lon_grid_0)
        st.session_state.map_bounds = [[min_lat, min_lon], [max_lat, max_lon]]

    # Build Folium map with fixed center and bounds
    map = folium.Map(location=st.session_state.map_center, tiles="Cartodb Positron", max_bounds=True)
    map.fit_bounds(st.session_state.map_bounds)

    # Initialize FeatureGroup
    featureGroup = FeatureGroup(name="rainfall_heatmap")

    # Initialize frame data
    n = frames[st.session_state.frame_idx]

    # for n in frames:
    lat_grid_frame, lon_grid_frame, rainfall_frame = generate_radar_data(f"prediction_+{n}min.json")

    # Build HeatMap
    heat_data = []
    for i in range(lat_grid_frame.shape[0]):
        for j in range(lon_grid_frame.shape[1]):
            lat = lat_grid_frame[i, j]
            lon = lon_grid_frame[i, j]
            rain = rainfall_frame[i, j]
            heat_data.append([lat, lon, rain])
    
    HeatMap(heat_data,
            min_opacity=0,
            gradient=GRADIENT).add_to(featureGroup)

    if "marker_location" in st.session_state:
        Marker(location=st.session_state.marker_location,
                draggable=True).add_to(featureGroup)

    # Display Folium map
    with map_container.container():
        map_display = st_folium(map,
                                width=800,
                                height=500,
                                feature_group_to_add=featureGroup,
                                key="animated_heatmap")

        # Update marker position immediately after each click
        if map_display.get("last_clicked"):
            lat, lng = map_display["last_clicked"]["lat"], map_display["last_clicked"]["lng"]
            st.session_state.marker_location = [lat, lng]

        # Map descriptions
        st.markdown(f"**🕒 Forecast Interval:** +{n} minutes")
        if "marker_location" in st.session_state:
            st.markdown(f"**📍 Marker Coordinates:** {st.session_state.marker_location}")

    # Move to next rainfall heatmap frame
    st.session_state.frame_idx = (st.session_state.frame_idx + 1) % len(frames)

    # Rerun after a short delay
    time.sleep(0.1)
    st.rerun()
