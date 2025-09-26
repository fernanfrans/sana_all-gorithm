import streamlit as st
from datetime import datetime

def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ Controls")
        st.markdown("#### Radar Settings")
        st.selectbox("Update Interval", ["Real-time", "5 minutes", "15 minutes", "30 minutes"])
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
