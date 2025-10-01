import streamlit as st
from backend.data_loader import load_rainloop_data

def render_nowcasting():
    st.markdown("### 📊 RAINLOOP Nowcasting Data")
    processed_data = load_rainloop_data()

    if processed_data:
        st.success("✅ RAINLOOP backend data loaded successfully!")
        st.json(processed_data)
    else:
        st.error("❌ Could not load RAINLOOP backend data")
