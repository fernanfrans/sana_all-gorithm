import streamlit as st
import requests
from datetime import datetime, timedelta

def render_weather():
    # --- CONFIG ---
    API_KEY = "INSERT_API"  # Replace with your actual OpenWeatherMap API key
    CITY = "Quezon City,PH"  
    AUTO_UPDATE_INTERVAL = 5  # minutes

    # --- DYNAMIC TITLE ---
    city_display = CITY.replace(",PH", "")
    st.markdown(f"### 🌤️ Current Weather - {city_display}")

    # --- WEATHER API URL ---
    URL = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&units=metric&appid={API_KEY}"

    # --- SESSION STATE INIT ---
    if "weather_data" not in st.session_state:
        st.session_state.weather_data = None
        st.session_state.last_updated = None

    # --- FETCH WEATHER FUNCTION ---
    def fetch_weather():
        """Fetch latest weather data and update session state."""
        try:
            response = requests.get(URL)
            data = response.json()

            if data.get("cod") != 200:
                st.error(f"Error fetching weather: {data.get('message')}")
                return

            st.session_state.weather_data = data
            st.session_state.last_updated = datetime.utcnow() + timedelta(hours=8)  # PH time
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
    if st.button("🔄 Refresh Now"):
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
