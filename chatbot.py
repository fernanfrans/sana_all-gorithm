import os
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as gen_ai

# Load environment variables from .env file
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Streamlit page
st.set_page_config(
    page_title="RAINLOOP Chatbot",
    page_icon="⛈️",
    layout="centered"
)

# Validate API key
if not GEMINI_API_KEY:
    st.error("Missing Google API key. Please set GEMINI_API_KEY in your .env file.")
    st.stop()

# Configure Gemini API
gen_ai.configure(api_key=GEMINI_API_KEY)

# Use Gemini 2.5 Flash with API version v1
model = gen_ai.GenerativeModel(model_name="gemini-2.5-pro")

# Translate Gemini role to Streamlit role
def translate_role(role):
    return "assistant" if role == "model" else role

# Initialize chat session
if "chat_session" not in st.session_state:
    st.session_state.chat_session = model.start_chat(history=[])

# App title
st.title("⛈️ RAINLOOP Chatbot")

# Display chat history
for msg in st.session_state.chat_session.history:
    with st.chat_message(translate_role(msg.role)):
        st.markdown(msg.parts[0].text)

# Chat input
user_input = st.chat_input("Ask RAINLOOP Chatbot...")
if user_input:
    st.chat_message("user", avatar="🧑‍💻").markdown(user_input)
    response = st.session_state.chat_session.send_message(user_input)
    with st.chat_message("assistant", avatar="⛈️"):
        st.markdown(response.text)
