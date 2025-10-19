import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Build path to ../config/.env.example relative to this file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '../config/.env.example')

# Load the environment variables
load_dotenv(dotenv_path=CONFIG_PATH, override=True)

def get_client() -> Client:
    """
    Create and return a Supabase client using the credentials
    from config/.env.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY in config/.env.example")

    return create_client(url, key)
