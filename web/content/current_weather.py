import streamlit as st
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os


def render_weather():
    # --- CONFIG ---
    API_KEY = os.getenv("MAP_API_KEY")
    NOMATIM_URL = os.getenv("NOMATIM_URL")
    # --- Initialize marker_location safely ---
    if st.session_state.marker_location:
        lat = st.session_state.marker_location[0]
        lon = st.session_state.marker_location[1]
    else:
        lat, lon = 41.151920318603516, -104.8060302734375  # Default radar origin location
    
    # do reverse geocoding to get city name using Nominatim HTTP API
    CITY = "Selected Location"
    try:
        nominatim_params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 14,
            "addressdetails": 1,
        }
        nominatim_headers = {"User-Agent": "RainLoop-Nowcast/1.0 (contact: support@rainloop.ai)"}
        response = requests.get(NOMATIM_URL,
            params=nominatim_params,
            headers=nominatim_headers,
            timeout=5,
        )
        response.raise_for_status()
        geo_payload = response.json()
        CITY = geo_payload.get("display_name") or CITY
    except Exception:
        pass

    AUTO_UPDATE_INTERVAL = 5

    # --- DYNAMIC TITLE ---
    city_display = CITY.replace(",PH", "").strip()
    st.markdown(f"### 🌤️ Current Weather - {city_display}")

    # --- WEATHER API URL ---
    URL = os.getenv("WEATHER_URL")
    params = {"lat": lat, "lon": lon, "units": "metric", "appid": API_KEY}
    response = requests.get(URL, params=params)
    data = response.json()

    # --- SESSION STATE INIT ---
    if "weather_data" not in st.session_state:
        st.session_state.weather_data = None
        st.session_state.last_updated = None

    # --- FETCH WEATHER FUNCTION ---
    def fetch_weather():
        """Fetch latest weather data and update session state."""
        try:
            if data.get("cod") != 200:
                st.error(f"Error fetching weather: {data.get('message')}")
                return

            st.session_state.weather_data = data
            st.session_state.last_updated = datetime.utcnow() + timedelta(hours=8)  
        except Exception as e:
            st.error(f"Failed to fetch weather: {e}")

    # --- AUTO UPDATE CHECK ---
    now = datetime.utcnow() + timedelta(hours=8)
    if (
        st.session_state.weather_data is None
        or st.session_state.last_updated is None
        or (now - st.session_state.last_updated).total_seconds() / 60 > AUTO_UPDATE_INTERVAL
    ):
        fetch_weather()

    # --- MANUAL REFRESH BUTTON ---
    if st.button("🔄 Refresh Weather", use_container_width=True):
        with st.spinner("Updating weather…"):
            fetch_weather()

    # --- DISPLAY WEATHER INFO ---
    if st.session_state.weather_data:
        data = st.session_state.weather_data
        weather_desc = data["weather"][0]["description"].upper()
        temp = data["main"]["temp"]
        temp_min = data["main"]["temp_min"]
        temp_max = data["main"]["temp_max"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        pressure = data["main"]["pressure"]
        icon_code = data["weather"][0]["icon"]
        icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png"
        last_updated = st.session_state.last_updated.strftime("%Y-%m-%d %H:%M:%S")

        st.markdown(f"""
        <div style="border: 2px solid #e0e0e0; border-radius: 10px; padding: 15px; margin-top: 10px; background-color: #fafafa;">
            <div style="display:flex; align-items:center; gap:15px;">
                <img src="{icon_url}" alt="weather icon" style="width:60px;height:60px;">
                <div>
                    <h3 style="margin:0; color:#003366;">{weather_desc} - {city_display}</h3>
                    <p><strong>Temp:</strong> {temp}°C (High: {temp_max:.2f}°C | Low: {temp_min:.2f}°C)</p>
                    <p><strong>Humidity:</strong> {humidity}% | <strong>Wind:</strong> {wind_speed} m/s</p>
                    <p><strong>Pressure:</strong> {pressure} hPa</p>
                    <p style="font-size:13px; color:gray;"><em>Last Updated:</em> {last_updated}</p>
                </div>
            </div>
        </div>
        <p style="font-size:12px; color:gray; margin-top:8px;">
            ⏱️ This section automatically updates every {AUTO_UPDATE_INTERVAL} minutes.  
            You can also click <strong>“Refresh Now”</strong> anytime to manually get the latest weather data.
        </p>
        """, unsafe_allow_html=True)
