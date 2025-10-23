import streamlit as st


def render_sidebar():
    with st.sidebar:
        st.markdown("#### Data Sources")
        st.markdown("- **Radar:** Doppler Weather Radar Network")
        st.markdown("- **Nowcasting:** RAINLOOP AI Model")  
        st.markdown("- **Satellite:** Himawari-8/9")
        st.markdown("- **Models:** GFS, ECMWF, JMA")

        
