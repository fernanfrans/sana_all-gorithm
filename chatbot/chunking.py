import json
import os

filepath = "chatbot-data/20250527_000900.json"

def load_weather_json(path=filepath):
    if not os.path.exists(path):
        print(f"Error: File '{path}' does not exist.")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from '{path}': {e}")
    except Exception as e:
        print(f"Unexpected error reading '{path}': {e}")
    return None

def chunk_weather_data(json_data):
    chunks = []
    for entry in json_data["weather_data"]:
        text = (
            f"{entry['place']} is located at latitude {entry['latitude']} and longitude {entry['longitude']}. "
            f"It has a reflectivity of {entry['reflectivity']} dBZ, indicating {entry['rain_category']} rain."
        )
        chunks.append({"text": text, "metadata": entry})
    return chunks
