import streamlit as st
from chatbot.bot_setup import CHAT_MODEL, gen_ai

def get_model():
    return gen_ai.GenerativeModel(model_name=CHAT_MODEL)

def get_chat_session():
    if "chat_session" not in st.session_state:
        model = get_model()
        st.session_state.chat_session = model.start_chat(history=[])
    return st.session_state.chat_session

def clear_chat_session():
    if "chat_session" in st.session_state:
        del st.session_state["chat_session"]
