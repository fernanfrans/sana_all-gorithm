import streamlit as st
from backend.predict import predict_main

def render_nowcasting():
    st.markdown("### 📊 RAINLOOP Nowcasting Data")
    processed_data = predict_main()

    if processed_data:
        st.success("✅ RAINLOOP backend data loaded successfully!")
        st.json(processed_data)
    else:
        st.error("❌ Could not load RAINLOOP backend data")
