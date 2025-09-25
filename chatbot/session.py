import streamlit as st
from config.settings import MODEL_NAME, gen_ai

def get_model():
    return gen_ai.GenerativeModel(model_name=MODEL_NAME)

def get_chat_session():
    if "chat_session" not in st.session_state:
        model = get_model()
        st.session_state.chat_session = model.start_chat(history=[])
    return st.session_state.chat_session
