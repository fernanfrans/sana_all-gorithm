import json
import os

def load_rainloop_data(file_path="backend/rainloop_data.json"):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                return json.load(f)
            except:
                return None
    return None
