import streamlit as st
from streamlit_autorefresh import st_autorefresh
from backend.predict import predict_main

def render_nowcasting():
    st.markdown("### 📊 RAINLOOP Nowcasting Data")

    # Add a small refresh indicator and timer
    count = st_autorefresh(interval=10 * 60 * 1000, key="nowcasting_refresh")

    with st.spinner("Fetching latest radar data and predictions..."):
        try:
            processed_data = predict_main()
            if processed_data:
                st.success(f"✅ RAINLOOP backend data updated successfully! (Refresh #{count})")
            else:
                st.warning("⚠️ No new data available yet.")
        except Exception as e:
            st.error(f"❌ Error while running nowcasting: {e}")
