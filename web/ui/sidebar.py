import streamlit as st
from datetime import datetime

def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ Controls")
        st.markdown("#### Radar Settings")
        st.select_slider("Update Interval", ["5 mins", "10 mins", "15 mins", "20 mins", "25 mins", "30 mins", "35 mins", "40 mins", "45 mins", "50 mins", "55 mins", "60 mins", "65 mins", "70 mins", "75 mins", "80 mins", "85 mins", "90 mins", "95 mins", "100 mins", "105 mins", "110 mins", "115 mins", "120 mins"])
        st.checkbox("Show Typhoon Track", value=True)
        st.checkbox("Show Warning Areas", value=True)

        st.markdown("#### Data Sources")
        st.markdown("- **Radar:** Doppler Weather Radar Network")
        st.markdown("- **Nowcasting:** RAINLOOP AI Model")  
        st.markdown("- **Satellite:** Himawari-8/9")
        st.markdown("- **Models:** GFS, ECMWF, JMA")

        st.markdown("#### Last Updated")
        st.markdown(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")

        if st.button("🔄 Refresh Data"):
            st.rerun()
