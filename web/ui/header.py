import streamlit as st

def render_header():
    col1, col2, col3 = st.columns([1,3,1])
    with col2:
        st.image("assets/logo1.png", use_container_width=True)
