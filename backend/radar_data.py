import os
import json
import numpy as np
import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

def init_supabase():
    dotenv_path = os.path.join(os.path.dirname(__file__), '../config/.env.example')
    load_dotenv(dotenv_path)
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    BUCKET_NAME_PREDICTED = os.getenv("BUCKET_PREDICTED")
    BUCKET_NAME_NC = os.getenv("BUCKET_NC")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return client, BUCKET_NAME_PREDICTED, BUCKET_NAME_NC

@st.cache_data
def generate_radar_data():
    supabase_client, bucket_predicted, bucket_nc = init_supabase()
    
    predicted_data = {}
    files = supabase_client.storage.from_(bucket_predicted).list()
    for i, f in enumerate(filter(lambda x: x["name"].startswith("RAW"), files)):
        data_bytes = supabase_client.storage.from_(bucket_predicted).download(f["name"])
        data = json.loads(data_bytes.decode("utf-8"))
        predicted_data[f"+{(i+1)*5}min"] = data
    return predicted_data
