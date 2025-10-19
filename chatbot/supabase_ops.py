import json
import datetime as dt
from typing import Any, Dict, List
from chatbot.supabase_client import get_client

BUCKET = "radar-predicted"

def upload_json(path_in_bucket: str, payload: Dict[str, Any]) -> str:
    sb = get_client()
    data_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    res = sb.storage.from_(BUCKET).upload(
        path_in_bucket,
        data_bytes,
        {"contentType": "application/json", "upsert": True},
    )

    # Build a public URL (works because bucket is public)
    public_url = sb.storage.from_(BUCKET).get_public_url(path_in_bucket)
    return public_url

def list_files(prefix: str = "") -> List[str]:
    sb = get_client()
    items = sb.storage.from_(BUCKET).list(path=prefix)
    return [item["name"] for item in items]

def download_file(path_in_bucket: str) -> bytes:
    sb = get_client()
    return sb.storage.from_(BUCKET).download(path_in_bucket)

