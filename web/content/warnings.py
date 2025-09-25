import streamlit as st

def render_warnings():
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
