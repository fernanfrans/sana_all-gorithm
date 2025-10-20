import os
import json
import numpy as np
import streamlit as st

# TODO: Get prediction data from Supabase instead
@st.cache_data
def generate_radar_data(filename):
    # Get the absolute path to the prediction results file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "predicted_json", filename)
    
    # Open and load the JSON file
    with open(json_path, "r") as f:
        data = json.load(f)

    # Extract coordinate arrays
    coords = data["coordinates"]

    # Convert to NumPy arrays
    lat_grid = np.array(coords["lat"])
    lon_grid = np.array(coords["lon"])
    reflectivity = np.array(data["reflectivity"])
    return lat_grid, lon_grid, reflectivity
