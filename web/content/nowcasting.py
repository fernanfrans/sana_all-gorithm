import streamlit as st
from backend.radar_data import generate_radar_data

def render_nowcasting():
    st.markdown("### 📊 RAINLOOP Nowcasting Data")

    processed_data = generate_radar_data()

    if processed_data:
        if not st.session_state.get("nowcasting_data_loaded"):
            st.success("✅ RAINLOOP backend data loaded successfully!")
        else:
            st.caption("✅ RAINLOOP backend data ready.")
        st.session_state["nowcasting_data_loaded"] = True
        st.session_state.prediction_data = processed_data
    else:
        st.error("❌ Could not load RAINLOOP backend data")
        st.session_state["nowcasting_data_loaded"] = False
