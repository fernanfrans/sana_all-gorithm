import streamlit as st
from web.ui.header import render_header
from web.ui.sidebar import render_sidebar
from web.ui.banner import render_banner
from web.ui.styles import inject_styles
from web.content.warnings import render_warnings
from web.content.current_weather import render_weather
from web.content.nowcasting import render_nowcasting
from web.content.radar import render_radar
# from chatbot.bot import run_chatbot

# Page config
st.set_page_config(
    page_title="RAINLOOP - Local Precipitation Nowcasting",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inject styles
inject_styles()

# Banner
render_banner()

# Header
render_header()

# Layout
col1, col2 = st.columns([1, 2])

with col1:
    render_nowcasting()
    render_warnings()
    render_weather()
    
with col2:
    render_radar()

# Sidebar
render_sidebar()

# Chatbot (isolated to avoid rerunning the entire layout on interactions)
if hasattr(st, "fragment"):
    @st.fragment
    def _chatbot_fragment():
        run_chatbot()

    _chatbot_fragment()
elif hasattr(st, "experimental_fragment"):
    _chatbot_fragment = st.experimental_fragment(run_chatbot)
    _chatbot_fragment()
else:
    run_chatbot()


