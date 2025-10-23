import os
from supabase import create_client, Client
from dotenv import load_dotenv
import streamlit as st
# Build path to ../config/.env.example relative to this file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '../config/.env.example')

# Load the environment variables
load_dotenv(dotenv_path=CONFIG_PATH, override=True)

def get_client() -> Client:
    """
    Create and return a Supabase client using the credentials
    from config/.env.
    """
    # Prefer Streamlit secrets for Streamlit runtime; fallback to environment
    url = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

    if not url or not key:
       raise ValueError(
            "Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_KEY via environment or .streamlit/secrets.toml."
        )

    return create_client(url, key)
