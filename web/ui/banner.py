import streamlit as st

def render_banner():
    st.markdown("""
    <div class="banner">
    RAINLOOP nowcasting data updated every 5 minutes | Radar data updated every 6 minutes
</div>
    """, unsafe_allow_html=True)
