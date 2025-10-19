import json
import os
from datetime import datetime

LOG_DIR = "chatbot-data/logs"
os.makedirs(LOG_DIR, exist_ok=True)

def _get_log_path():
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"{today}.json")

def log_entry(entry: dict):
    path = _get_log_path()
    entry_with_time = {"timestamp": datetime.now().isoformat(), **entry}
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)
    try:
        with open(path, "r", encoding="utf-8") as f:
            logs = json.load(f)
            if not isinstance(logs, list):
                logs = []
    except (json.JSONDecodeError, FileNotFoundError):
        logs = []
    logs.append(entry_with_time)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

def log_chat(user_input: str, response: str, mode="chatbot"):
    log_entry({"mode": mode, "user_input": user_input, "response": response})
