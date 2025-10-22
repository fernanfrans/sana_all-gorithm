# chatbot/chunking.py (keep your version if you already added streaming)
import json, os
from typing import Dict, Generator

def _stream_entries(path: str) -> Generator[Dict, None, None]:
    try:
        import ijson  # pip install ijson
        with open(path, "rb") as f:
            for entry in ijson.items(f, "weather_data.item"):
                if isinstance(entry, dict):
                    yield entry
    except ImportError:
        data = json.load(open(path, "r", encoding="utf-8"))
        for entry in data.get("weather_data", []):
            yield entry

def format_entry_as_text(entry: Dict) -> str:
    place = entry.get("place", "Unknown place")
    lat = entry.get("latitude", "N/A")
    lon = entry.get("longitude", "N/A")
    refl = entry.get("reflectivity", "N/A")
    cat = entry.get("rain_category", "Unknown")
    return f"{place}: lat {lat}, lon {lon}. Reflectivity {refl} dBZ → {cat} rain."

def chunk_iter_from_file(path: str) -> Generator[Dict, None, None]:
    for entry in _stream_entries(path):
        yield {"text": format_entry_as_text(entry), "metadata": entry}
