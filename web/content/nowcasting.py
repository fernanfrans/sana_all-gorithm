import streamlit as st
from streamlit_autorefresh import st_autorefresh
from backend.predict import predict_main

def render_nowcasting():
    st.markdown("### 📊 RAINLOOP Nowcasting Data")

    # Auto-refresh every 10 minutes
    count = st_autorefresh(interval=10 * 60 * 1000, key="nowcasting_refresh")

    if "has_run" not in st.session_state or st.session_state.get("refresh_id") != count:
        st.session_state.refresh_id = count
        st.session_state.has_run = True

        with st.spinner("Fetching latest radar data and predictions..."):
            try:
                processed_data = predict_main()
                if processed_data:
                    st.success(f"✅ RAINLOOP data updated successfully! (Refresh #{count})")
                else:
                    st.warning("⚠️ No new data available yet.")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    else:
        st.info(f"🟢 Waiting until next refresh cycle ({count}).")
