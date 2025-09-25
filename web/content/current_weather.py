import streamlit as st

def render_weather():
    st.markdown("### 🌤️ Current Weather - Port Area, Metro Manila")
    st.markdown("""
    <div class="weather-current">
        <h3>LIGHT RAINS</h3>
        <p><strong>High:</strong> 29°C | <strong>Low:</strong> 24°C</p>
        <p><strong>Humidity:</strong> 85% | <strong>Wind:</strong> WSW 15 km/h</p>
        <p><strong>Pressure:</strong> 1011 hPa</p>
    </div>
    """, unsafe_allow_html=True)
