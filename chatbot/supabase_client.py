import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Build path to ../config/.env relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # goes up from data_loader/
CONFIG_PATH = os.path.join(BASE_DIR, "config", ".env")

# Load the environment variables
load_dotenv(dotenv_path=CONFIG_PATH)

def get_client() -> Client:
    """
    Create and return a Supabase client using the credentials
    from config/.env.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY in config/.env")

    return create_client(url, key)
