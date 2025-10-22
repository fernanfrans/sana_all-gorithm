import streamlit as st
from backend.predict import predict_main
from backend.radar_data import generate_radar_data

def render_nowcasting():
    st.markdown("### 📊 RAINLOOP Nowcasting Data")
    predict = predict_main()
    if predict:
        processed_data = generate_radar_data()

    if processed_data:
        st.success("✅ RAINLOOP backend data loaded successfully!")
        st.session_state.prediction_data = processed_data
        st.json(processed_data)
    else:
        st.error("❌ Could not load RAINLOOP backend data")