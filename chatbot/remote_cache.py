# chatbot/remote_cache.py
import os
from pathlib import Path

from chatbot.supabase_ops import download_file

CACHE_DIR = os.getenv("RAINLOOP_CACHE_DIR", "chatbot-cache")
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

def ensure_local_from_supabase(path_in_bucket: str) -> str:
    """
    Downloads bytes from Supabase (if not cached) to chatbot-cache/<basename>.
    Returns local filepath.
    """
    local_path = Path(CACHE_DIR) / os.path.basename(path_in_bucket)
    if not local_path.exists():
        data = download_file(path_in_bucket)  # bytes from your supabase_ops.py
        local_path.write_bytes(data)
    return str(local_path)
