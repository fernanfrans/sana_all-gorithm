import os
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as gen_ai

load_dotenv()

# Fallback logic: Cloud first, then local
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY") 

if not GEMINI_API_KEY:
    raise ValueError("Missing Google API key. Please set GEMINI_API_KEY in your .env file.")

# Configure Gemini API once
gen_ai.configure(api_key=GEMINI_API_KEY)

# Model Config
MODEL_NAME = "gemini-2.5-pro"
