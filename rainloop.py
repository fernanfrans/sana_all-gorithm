import streamlit as st
from web.ui.header import render_header
from web.ui.sidebar import render_sidebar
from web.ui.banner import render_banner
from web.ui.styles import inject_styles
from web.content.warnings import render_warnings
from web.content.current_weather import render_weather
from web.content.nowcasting import render_nowcasting
from web.content.radar import render_radar
from chatbot.bot import run_chatbot

# Page config
st.set_page_config(
    page_title="RAINLOOP - Local Precipitation Nowcasting",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="collapsed"
)



# Inject styles + Header
inject_styles()

# Banner
render_banner()

# Header
render_header()

# Layout
col1, col2 = st.columns([1, 2])

with col1:
    render_warnings()
    render_weather()
    render_nowcasting()

with col2:
    render_radar()

# Sidebar
render_sidebar()

# Chatbot
run_chatbot()



