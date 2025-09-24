import streamlit as st
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import os

# Page configuration
st.set_page_config(
    page_title="RAINLOOP - Local Precipitation Nowcasting",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main > div { padding-top: 1rem; }
    .stApp > header { background-color: transparent; }
    .header-container {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 0.5rem 1rem;
        margin: -1rem -1rem 1rem -1rem;
        border-bottom: 3px solid #fbbf24;
    }
    .header-title { color: white; font-size: 1.5rem; font-weight: bold; margin: 0; }
    .header-subtitle { color: #e5e7eb; font-size: 0.9rem; margin: 0; }
    .warning-card { background: linear-gradient(90deg, #dc2626 0%, #ef4444 100%); color: white; padding: 0.75rem; border-radius: 0.5rem; margin: 0.5rem 0; border-left: 4px solid #fbbf24; }
    .advisory-card { background: linear-gradient(90deg, #0891b2 0%, #06b6d4 100%); color: white; padding: 0.75rem; border-radius: 0.5rem; margin: 0.5rem 0; border-left: 4px solid #fbbf24; }
    .info-card { background: linear-gradient(90deg, #059669 0%, #10b981 100%); color: white; padding: 0.75rem; border-radius: 0.5rem; margin: 0.5rem 0; border-left: 4px solid #fbbf24; }
    .weather-current { background: rgba(30, 58, 138, 0.1); border-radius: 0.5rem; padding: 1rem; border: 1px solid #3b82f6; }
    .chatbot-container { background: #f8fafc; border-radius: 0.5rem; padding: 1rem; border: 2px solid #e2e8f0; margin-top: 1rem; }
    .chat-message { background: white; border-radius: 0.5rem; padding: 0.75rem; margin: 0.5rem 0; border-left: 4px solid #3b82f6; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .radar-container { border: 2px solid #1e3a8a; border-radius: 0.5rem; padding: 0.5rem; background: #000; }
    .metric-card { background: white; border-radius: 0.5rem; padding: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid #3b82f6; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="header-container">
    <h1 class="header-title">🌧️ RAINLOOP - Local Precipitation Nowcasting</h1>
    <p class="header-subtitle">Radar AI Nowcasting for Local Observation of Precipitation (RAINLOOP)</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state for chat
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Function to generate sample radar data
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
    rainfall = np.maximum(rainfall, 0)
    return lat_grid, lon_grid, rainfall

# Load RAINLOOP nowcasting backend data
def load_rainloop_data(file_path="backend/rainloop_data.json"):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                data = json.load(f)
                return data
            except:
                return None
    return None

processed_data = load_rainloop_data()

# Main layout
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 🚨 Active Warnings")
    st.markdown("""
    <div class="warning-card">
        <strong>⚠️ Tropical Cyclone NANDO and Southwest Monsoon</strong><br>
        Heavy rainfall outlook due to TC NANDO Forecast Rainfall Today to Tomorrow...
        <a href="#" style="color: #fbbf24;">See More</a>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="advisory-card">
        <strong>📢 RAINLOOP Advisory</strong><br>
        Stay informed about local precipitation events and heavy rainfall warnings...
        <a href="#" style="color: #fbbf24;">See More</a>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🌤️ Current Weather - Port Area, Metro Manila")
    st.markdown("""
    <div class="weather-current">
        <h3>LIGHT RAINS</h3>
        <p><strong>High:</strong> 29°C | <strong>Low:</strong> 24°C</p>
        <p><strong>Humidity:</strong> 85% | <strong>Wind:</strong> WSW 15 km/h</p>
        <p><strong>Pressure:</strong> 1011 hPa</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📊 RAINLOOP Nowcasting Data")
    if processed_data:
        st.success("✅ RAINLOOP backend data loaded successfully!")
        st.json(processed_data)
    else:
        st.error("❌ Could not load RAINLOOP backend data")

with col2:
    st.markdown("### 🎯 Weather Radar - Real-time Precipitation")
    lat_grid, lon_grid, rainfall = generate_radar_data()
    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=rainfall,
        x=lon_grid[0],
        y=lat_grid[:, 0],
        colorscale=[
            [0, 'rgba(0,0,0,0)'],
            [0.1, '#000080'],
            [0.3, '#0080FF'],
            [0.5, '#00FF00'],
            [0.7, '#FFFF00'],
            [0.8, '#FF8000'],
            [1.0, '#FF0000']
        ],
        hovertemplate='Lat: %{y:.2f}<br>Lon: %{x:.2f}<br>Rainfall: %{z:.1f} mm/hr<extra></extra>',
        name='Rainfall Intensity'
    ))
    fig.add_trace(go.Scatter(
        x=[121.0],
        y=[14.5],
        mode='markers+text',
        marker=dict(size=20, color='white', symbol='circle', line=dict(color='red', width=3)),
        text=['🌀 NANDO'],
        textposition="top center",
        textfont=dict(size=14, color='white'),
        name='Typhoon Center'
    ))
    fig.update_layout(
        title=dict(
            text="Doppler Radar - Super Typhoon NANDO<br><sub>Updated: " + datetime.now().strftime("%Y-%m-%d %H:%M UTC") + "</sub>",
            x=0.5, font=dict(color='white', size=16)
        ),
        xaxis=dict(title="Longitude", color='white', gridcolor='gray'),
        yaxis=dict(title="Latitude", color='white', gridcolor='gray'),
        plot_bgcolor='black', paper_bgcolor='black', font=dict(color='white'),
        height=500, showlegend=False
    )
    st.markdown('<div class="radar-container">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Chatbot section
st.markdown("---")
st.markdown("### 🤖 Weather Assistant - Ask me...")

chatbot_col1, chatbot_col2 = st.columns([3, 1])
with chatbot_col1:
    user_input = st.text_input("Ask about weather conditions, forecasts, or warnings:", placeholder="E.g., What's the current status of Typhoon Nando?")
with chatbot_col2:
    send_button = st.button("Send 📤", type="primary")

def get_weather_response(question):
    responses = {
        "nando": "Super Typhoon Nando is moving towards northern Luzon with maximum sustained winds of 185 km/h. Heavy rainfall expected in Metro Manila and nearby provinces.",
        "rainfall": "Current rainfall forecast shows heavy to intense rainfall (50-100mm) in the next 6 hours over Metro Manila due to TC Nando and enhanced southwest monsoon.",
        "warning": "Active warnings include Typhoon Signal No. 3 for Metro Manila and nearby areas. Flash flood and landslide warnings in effect.",
        "safety": "Stay indoors, avoid flood-prone areas, keep emergency supplies ready, and monitor official PAGASA updates."
    }
    question_lower = question.lower()
    for key, response in responses.items():
        if key in question_lower:
            return response
    return "I can help you with weather information about Typhoon Nando, rainfall forecasts, and active warnings. What would you like to know?"

if send_button and user_input:
    st.session_state.chat_history.append({"role": "user", "message": user_input, "timestamp": datetime.now().strftime("%H:%M")})
    response = get_weather_response(user_input)
    st.session_state.chat_history.append({"role": "assistant", "message": response, "timestamp": datetime.now().strftime("%H:%M")})

# Display chat history
if st.session_state.chat_history:
    st.markdown('<div class="chatbot-container">', unsafe_allow_html=True)
    for chat in st.session_state.chat_history[-6:]:
        if chat["role"] == "user":
            st.markdown(f"<div class='chat-message'><strong>👤 You ({chat['timestamp']}):</strong><br>{chat['message']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-message'><strong>🤖 Weather Assistant ({chat['timestamp']}):</strong><br>{chat['message']}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Controls")
    st.markdown("#### Radar Settings")
    radar_update = st.selectbox("Update Interval", ["Real-time", "5 minutes", "15 minutes", "30 minutes"])
    show_typhoon_track = st.checkbox("Show Typhoon Track", value=True)
    show_warnings = st.checkbox("Show Warning Areas", value=True)
    st.markdown("#### Data Sources")
    st.markdown("- **Radar:** Doppler Weather Radar Network")
    st.markdown("- **Nowcasting:** RAINLOOP AI Model")  
    st.markdown("- **Satellite:** Himawari-8/9")
    st.markdown("- **Models:** GFS, ECMWF, JMA")
    st.markdown("#### Last Updated")
    st.markdown(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    if st.button("🔄 Refresh Data"):
        st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6b7280; font-size: 0.8rem;">
    <p>Department of Science and Technology - Philippine Atmospheric, Geophysical and Astronomical Services Administration</p>
    <p>RAINLOOP nowcasting data updated every 5 minutes | Radar data updated every 6 minutes</p>
</div>
""", unsafe_allow_html=True)
