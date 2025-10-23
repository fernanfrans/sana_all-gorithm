import streamlit as st
import numpy as np
from backend.radar_data import generate_radar_data

def rain_category(dbz: float) -> str:
    """Categorize reflectivity (dBZ)."""
    if dbz is None or (isinstance(dbz, float) and np.isnan(dbz)):
        return "Unknown"
    if dbz > 65:
        return "Extremely heavy rain"
    if dbz >= 50:
        return "Heavy rain"
    if dbz >= 40:
        return "Moderate rain"
    if dbz >= 20:
        return "Light rain"
    return "Very light rain"

def get_reflectivity_at(lat, lon, prediction_frame):
    """Return reflectivity at nearest grid point to given lat/lon."""
    lat_grid = np.array(prediction_frame["coordinates"]["lat"])
    lon_grid = np.array(prediction_frame["coordinates"]["lon"])
    refl_grid = np.array(prediction_frame["reflectivity"])

    dist = (lat_grid - lat)**2 + (lon_grid - lon)**2
    idx = np.unravel_index(np.argmin(dist), dist.shape)
    return refl_grid[idx]

def get_advisory(category: str) -> str:
    """Return precautionary measures based on rain category."""
    if category == "Extremely heavy rain":
        return ("⚠️ Extremely heavy rain expected. Stay indoors, avoid flood-prone areas, "
                "secure outdoor items, and monitor local alerts.")
    elif category == "Heavy rain":
        return ("⚠️ Heavy rain expected. Carry an umbrella, avoid low-lying roads, "
                "and stay cautious when traveling.")
    elif category == "Moderate rain":
        return ("🌧️ Moderate rain expected. Carry an umbrella and plan for wet conditions.")
    elif category == "Light rain":
        return ("🌦️ Light rain expected. An umbrella might be useful if going outside.")
    elif category == "Very light rain":
        return ("☔ Very light rain. Minimal precautions needed, but stay aware.")
    else:
        return ("✅ No significant rainfall expected. Enjoy your day!")

def render_warnings():
    # --- Initialize marker_location safely ---
    st.markdown("### 🚨 Active Warnings")
    if "marker_location" not in st.session_state:
        st.session_state.marker_location = None

    if st.session_state.marker_location is None:
        # st.markdown(
        #     """ 
        #     <div style="
        #       border-radius: 8px; 
        #       padding: 10px; 
        #       background-color: #ffe5e5; 
        #       color: #000000; 
        #       font-weight: 600; 
        #     "> 
        #     📍 Please select a location on the radar map first.
        #       </div> 
        #       """, unsafe_allow_html=True)
        # return
        lat, lon = 41.151920318603516, -104.8060302734375  # Default radar origin location
    else:
        lat, lon = st.session_state.marker_location

    # --- Load radar prediction data ---
    if "prediction_data" not in st.session_state or not st.session_state.prediction_data:
        st.session_state.prediction_data = generate_radar_data()

    # --- Get reflectivity at marker location ---
    refl_5min = get_reflectivity_at(lat, lon, st.session_state.prediction_data["+5min"])
    refl_120min = get_reflectivity_at(lat, lon, st.session_state.prediction_data["+120min"])

    # --- Compute change over last 2 hours ---
    last_2_hours = refl_120min - refl_5min

    # --- Categorize rainfall ---
    if last_2_hours > 0:
        category = rain_category(last_2_hours)
        st.session_state.warning_message = f"⚠️ {category} expected in the next 2 hours."
    else:
        category = "No significant rainfall"
        st.session_state.warning_message = "✅ No significant rainfall expected in the next 2 hours."

    # --- Display warning ---
    st.markdown(f"""
    <div class="warning-card" style="border:1px solid #f00; padding:10px; border-radius:8px; background-color:#ffe5e5;">
        <strong>{st.session_state.warning_message}</strong><br>
        <em>Reflectivity change: {last_2_hours:.2f} dBZ — Category: {category}</em>
    </div>
    """, unsafe_allow_html=True)

    # --- Advisory card ---
    advisory_message = get_advisory(category)
    card_colors = {
        "Extremely heavy": "#ff4d4d",
        "Heavy": "#ff9999",
        "Moderate": "#ffcc66",
        "Light": "#ffff99",
        "Very light": "#d9f0ff",
        "No significant rainfall": "#d9ffd9"
    }
    card_color = card_colors.get(category, "#ffffff")

    st.markdown(f"""
    <div class="advisory-card" style="border:1px solid #ccc; padding:10px; border-radius:8px; background-color:{card_color};">
        <strong>📢 RAINLOOP Advisory</strong><br>
        {advisory_message}<br>
    </div>
    """, unsafe_allow_html=True)