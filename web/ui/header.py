import streamlit as st

def render_header():
    st.markdown("""
    <div class="header-container">
        <h1 class="header-title">🌧️ RAINLOOP - Local Precipitation Nowcasting</h1>
        <p class="header-subtitle">Radar AI Nowcasting for Local Observation of Precipitation (RAINLOOP)</p>
    </div>
    """, unsafe_allow_html=True)

