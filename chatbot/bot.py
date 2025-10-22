# chatbot/bot.py
import math
import streamlit as st
from datetime import datetime, timedelta, timezone

from chatbot.session import get_chat_session, clear_chat_session
from chatbot.query_time import extract_offset_minutes
from chatbot.file_selector_supabase import MANILA_TZ, nearest_lead_minutes
from chatbot.supabase_ops import (
    latest_complete_run_dir,
    load_manifest,
    fetch_record_json,
    resolve_offset_for_location,
)
from chatbot.location_lookup import rank_locations

st.set_page_config(page_title="RainLoop AI Assistant", page_icon="🌧️", layout="wide")


# ---------------- Session helpers ----------------

def _ensure_session_state():
    """Initialize all session_state keys used by the app."""
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "chat_session" not in st.session_state:
        try:
            st.session_state["chat_session"] = get_chat_session()
        except Exception:
            st.session_state["chat_session"] = None


def _append_message(role: str, avatar: str, content: str):
    st.session_state.setdefault("messages", [])
    st.session_state["messages"].append({"role": role, "avatar": avatar, "content": content})


# ---------------- Utility functions ----------------

def _format_local(dt: datetime) -> str:
    return dt.astimezone(MANILA_TZ).strftime("%Y-%m-%d %I:%M %p %Z")


def _valid_datetime(base_time_utc: datetime, lead_minutes: int) -> datetime:
    return base_time_utc + timedelta(minutes=int(lead_minutes))


def _display_run_freshness(base_time_utc: datetime):
    run_age = datetime.now(timezone.utc) - base_time_utc
    if run_age > timedelta(minutes=10):
        minutes_old = run_age.total_seconds() / 60
        st.warning(
            f"Latest run is {minutes_old:.1f} minutes old. A new update should arrive soon."
        )


# ---------------- Main app ----------------

def run_chatbot():
    _ensure_session_state()
    chat = st.session_state.get("chat_session") or get_chat_session()

    # Header & controls
    st.markdown("---")
    col1, col2, col3 = st.columns([13, 1, 1], gap="small")
    with col1:
        st.markdown("### 🦾🌧️ RainLoop AI Assistant - Ask me...💬")
    with col2:
        if st.button("↻ Restart"):
            st.session_state["messages"] = []
            clear_chat_session()
            st.success("Reset!")
    with col3:
        if st.button("🧹 Clear"):
            st.session_state["messages"] = []
            st.success("Clear!")

    # Display previous messages
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"], avatar=msg["avatar"]):
            st.markdown(msg["content"])

    # Input box
    query = st.chat_input("Ask RainLoop AI Assistant about weather conditions, forecasts, or warnings in your area!")

    error_message = "⚠️ No relevant weather data found for your query. Try another location or keyword."

    if query:
        timestamp = datetime.now().strftime("%I:%M %p")
        
        # Store and display user message
        user_msg = f"**[{timestamp}]** {query}"
        st.session_state["messages"].append({
            "role": "user",
            "avatar": "🧑‍💻",
            "content": user_msg
        })
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(user_msg)

        # Embed query and retrieve results
        query_emb = embed_query(query)
        results = retrieve(query, index, embeddings, query_emb)

        if not results:
            # No results found
            st.warning(error_message)
            st.session_state["messages"].append({
                "role": "assistant",
                "avatar": "🌧️",
                "content": error_message
            })
            log_chat(user_input=query, response=error_message, mode="rag")
        else:
            context = "\n".join([r["text"] for r in results])
            # Gemini Prompt
            prompt = (
                f"Act as the RadarLoop Weather Assistant that provides nowcasted information. "
                f"Using the following predicted weather information:\n{context}\n"
                f"Answer this question: {query} and provide short safety tips. "
                f"If place is not found, strictly state no information is available and enter other places, "
                f"do not summarize other info and do not give tips."
            )

            # Generate Gemini response
            with st.spinner("🌧️ RainLoop AI Assistant generating answer..."):
                try:
                    response = chat.send_message(prompt)
                    answer = response.text if hasattr(response, "text") else "⚠️ No response generated."
                except Exception as e:
                    answer = f"⚠️ Error generating response: {e}"

            # Store and display assistant message
            st.session_state["messages"].append({
                "role": "assistant",
                "avatar": "🌧️",
                "content": answer
            })
            with st.chat_message("assistant", avatar="🌧️"):
                st.markdown(answer)

            log_chat(user_input=query, response=answer, mode="rag")
