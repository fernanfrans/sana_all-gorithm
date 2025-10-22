import numpy as np
import streamlit as st
import folium
from streamlit_folium import folium_static, st_folium
from backend.radar_data import generate_radar_data
from folium.plugins import HeatMapWithTime, HeatMap
from folium import Map, Marker

def render_radar():
    # Use full-browser width
    st.set_page_config(layout="wide")
    st.markdown("### 🎯 Weather Radar - Real-Time Precipitation")
    
    # Heatmap gradient based on reflectivity value
    GRADIENT = {
        0.00: 'rgba(0,0,0,0)', # transparent (no rain)
        0.05: '#001040', # very light drizzle – dark navy
        0.10: '#0020A0', # light rain – blue
        0.20: '#0040FF', # light-moderate rain – bright blue
        0.30: '#00A0FF', # moderate rain – cyan
        0.40: '#00FFC0', # moderate-heavy rain – aqua green
        0.50: '#00FF00', # heavy rain – green
        0.60: '#A0FF00', # very heavy rain – lime
        0.70: '#FFFF00', # intense rain – yellow
        0.80: '#FFA000', # extreme rain – orange
        0.90: '#FF4040', # torrential – red-orange
        1.00: '#FF0000' # max reflectivity – bright red
    }
    
    # Set up frames
    frames = list(range(5, 125, 5))
    
    # Initialize session state
    if "map_center" not in st.session_state or "map_bounds" not in st.session_state:
        # Get initial latitude and longitude grids
        lat_grid_0, lon_grid_0, _ = generate_radar_data(f"prediction_+{frames[0]}min.json")
        
        # Set map center
        st.session_state.map_center = [np.mean(lat_grid_0), np.mean(lon_grid_0)]
        
        # Also set map bounds
        min_lat, max_lat = np.min(lat_grid_0), np.max(lat_grid_0)
        min_lon, max_lon = np.min(lon_grid_0), np.max(lon_grid_0)
        st.session_state.map_bounds = [[min_lat, min_lon], [max_lat, max_lon]]

    if "marker_location" not in st.session_state:
        st.session_state.marker_location = None

    if "selection_mode" not in st.session_state:
        st.session_state.selection_mode = False  # False = animated view, True = selection view
    
    col1, col2 = st.columns([4, 1])

    # Button for clearing marker
    with col1:
        if st.session_state.marker_location:
            if st.button("🗑️ Clear Marker"):
                st.session_state.marker_location = None
                st.rerun()
    # Button to toggle selection mode
    with col2:
        if not st.session_state.selection_mode:
            if st.button("📍 Select Location", use_container_width=True):
                st.session_state.selection_mode = True
                st.rerun()
        else:
            if st.button("◀️ View Animation", use_container_width=True):
                st.session_state.selection_mode = False
                st.rerun()
        
    # Build Folium map with fixed center and bounds
    map = Map(
        location=st.session_state.map_center,
        tiles="Cartodb Positron",
        max_bounds=True
    )
    map.fit_bounds(st.session_state.map_bounds)
    
    # SELECTION MODE - Interactive map with static heatmap
    if st.session_state.selection_mode:
        st.info("👆 Click on the map to place a marker")
        
        # Get the latest frame data
        lat_grid_latest, lon_grid_latest, rainfall_latest = generate_radar_data(f"prediction_+{frames[-1]}min.json")
        
        # Build static heatmap data for latest frame
        heat_data_latest = []
        for i in range(lat_grid_latest.shape[0]):
            for j in range(lon_grid_latest.shape[1]):
                lat = lat_grid_latest[i, j]
                lon = lon_grid_latest[i, j]
                rain = rainfall_latest[i, j]
                heat_data_latest.append([lat, lon, rain])
        
        # Add static HeatMap with latest frame
        HeatMap(
            heat_data_latest,
            min_opacity=0,
            gradient=GRADIENT
        ).add_to(map) 
        
        # Add existing marker if any
        if st.session_state.marker_location:
            Marker(
                location=st.session_state.marker_location,
                popup=f"Selected: {st.session_state.marker_location}",
                icon=folium.Icon(color='red')
            ).add_to(map)
        
        # Display with st_folium to capture clicks
        map_display = st_folium(
            map,
            width=None,
            height=600,
            key="selection_map",
            returned_objects=["last_clicked"]
        )
        
        # Capture click and update marker location
        if map_display and map_display.get("last_clicked"):
            new_location = [
                map_display["last_clicked"]["lat"],
                map_display["last_clicked"]["lng"]
            ]

            # Only update if location actually changed
            if st.session_state.marker_location != new_location:
                st.session_state.marker_location = new_location
                st.rerun()
        
        # Display current selection
        if st.session_state.marker_location:
            st.success(f"✓ Marker placed at: [{st.session_state.marker_location[0]:.4f}, {st.session_state.marker_location[1]:.4f}]")
    
    # ANIMATION MODE - Animated heatmap with folium_static
    else:
        # Prepare HeatMapWithTime data
        heat_data_seq = []
        for n in frames:
            lat_grid_frame, lon_grid_frame, rainfall_frame = generate_radar_data(f"prediction_+{n}min.json")
            
            # Build HeatMap for this frame
            heat_data = []
            for i in range(lat_grid_frame.shape[0]):
                for j in range(lon_grid_frame.shape[1]):
                    lat = lat_grid_frame[i, j]
                    lon = lon_grid_frame[i, j]
                    rain = rainfall_frame[i, j]
                    heat_data.append([lat, lon, rain])
            heat_data_seq.append(heat_data)
        
        # Add animated HeatMapWithTime
        HeatMapWithTime(
            heat_data_seq,
            index=[f"Predicted Reflectivity — +{n} min" for n in frames],
            auto_play=True,
            min_opacity=0,
            use_local_extrema=True,
            gradient=GRADIENT
        ).add_to(map)
        
        # Add marker if location exists
        if st.session_state.marker_location:
            Marker(
                location=st.session_state.marker_location,
                popup=f"Selected: {st.session_state.marker_location}",
                icon=folium.Icon(color='red')
            ).add_to(map)
        
        # Display animated map
        folium_static(map, width=None, height=600)
        
        # Show marker info if exists
        if st.session_state.marker_location:
            st.success(f"📍 Marker at: [{st.session_state.marker_location[0]:.4f}, {st.session_state.marker_location[1]:.4f}]")
