from supabase import create_client, Client
import os
from dotenv import load_dotenv
from torch import sort
import re
import json

# Import Data from supabase
def init_supabase():
    dotenv_path = os.path.join(os.path.dirname(__file__), '../../config/.env.example')  # use actual .env
    load_dotenv(dotenv_path)
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    BUCKET_NAME_PREDICTED = os.getenv("BUCKET_PREDICTED")
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase credentials not found in .env")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return client, BUCKET_NAME_PREDICTED

def get_predicted_data(supabase_client: Client, bucket_name: str):
    files = supabase_client.storage.from_(bucket_name).list()
    if not files:
        raise ValueError("No files found in Supabase bucket.")
    else:
        file_names = [f["name"] for f in files]

        sorted_files = sorted(file_names, key=extract_minutes)
        # print(f"Found {len(file_names)} files in Supabase bucket.")
        # print("Files:", sorted_files)
        predicted_data = []
        for file in sorted_files:
            radar_data = supabase_client.storage.from_(bucket_name).download(file)
            data = json.loads(radar_data)
            predicted_data.append(data)
        return predicted_data, sorted_files

def extract_minutes(filename):
    match = re.search(r'\+(\d+)min', filename)
    if match:
        return int(match.group(1))
    else:
        # if pattern not found, put at the start
        return -1
    