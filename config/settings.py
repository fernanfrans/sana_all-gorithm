import os
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as gen_ai



dotenv_path = os.path.join(os.path.dirname(__file__), '../config/.env.example')
load_dotenv(dotenv_path, override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY") 
if not GEMINI_API_KEY:
    raise ValueError(
        "Missing Google API key. Set GEMINI_API_KEY via environment or .streamlit/secrets.toml."
    )

gen_ai.configure(api_key=GEMINI_API_KEY)

CHAT_MODEL = "gemini-2.5-pro"
EMBEDDING_MODEL = "models/embedding-001"
