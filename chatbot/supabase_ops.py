import base64
import json
import struct
import time
import zlib
from typing import Any, Dict, List, Optional, Tuple

import requests

from chatbot.supabase_client import get_client

BUCKET = "radar-predicted"
RUNS_PREFIX = "runs"
LATEST_MARKER_PATH = "latest.txt"

_LATEST_CACHE: Dict[str, Any] = {"value": None, "expires": 0.0}
_MANIFEST_CACHE: Dict[str, Dict[str, Any]] = {}
_MANIFEST_EXPIRY: Dict[str, float] = {}
_LOOKUP_CACHE: Dict[Tuple[str, str], bytes] = {}


def _storage():
    return get_client().storage.from_(BUCKET)


def upload_json(path_in_bucket: str, payload: Dict[str, Any]) -> str:
    data_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    storage = _storage()
    storage.upload(
        path_in_bucket,
        data_bytes,
        {
            "contentType": "application/json",
            "upsert": "true",
        },
    )
    return storage.get_public_url(path_in_bucket)


def list_files(prefix: str = "") -> List[str]:
    storage = _storage()
    items = storage.list(path=prefix)
    return [item.get("name") for item in items if item.get("name")]


def download_file(path_in_bucket: str) -> bytes:
    return _storage().download(path_in_bucket)


def _get_public_url(path_in_bucket: str) -> str:
    return _storage().get_public_url(path_in_bucket)


def _extract_run_id_from_latest(contents: str) -> Optional[str]:
    first_line = contents.strip().splitlines()[0].strip() if contents.strip() else ""
    return first_line or None


def _discover_latest_run_via_listing() -> Optional[str]:
    """
    Fallback discovery if latest.txt is absent; inspects run folders.
    """
    storage = _storage()
    run_candidates: List[str] = []
    try:
        items = storage.list(path=RUNS_PREFIX)
    except Exception:
        items = []
    for item in items or []:
        name = item.get("name") or ""
        if not name:
            continue
        # Listing may return folder names ("20240601T1200Z") or paths ("20240601T1200Z/manifest.json")
        if name.endswith("/"):
            run_candidates.append(name.rstrip("/"))
        elif "/" not in name:
            run_candidates.append(name)
        elif name.endswith("manifest.json"):
            parts = name.split("/")
            if len(parts) >= 2:
                run_candidates.append(parts[0])
    if not run_candidates:
        return None
    run_candidates = sorted(set(run_candidates))
    return run_candidates[-1]


def latest_complete_run_dir(force_refresh: bool = False) -> Optional[str]:
    """
    Returns the latest run_id (without trailing slash). Cached for 60 seconds.
    """
    now = time.monotonic()
    if not force_refresh and now < _LATEST_CACHE.get("expires", 0.0):
        return _LATEST_CACHE.get("value")

    run_id: Optional[str] = None
    try:
        latest_bytes = download_file(LATEST_MARKER_PATH)
        run_id = _extract_run_id_from_latest(latest_bytes.decode("utf-8"))
    except Exception:
        run_id = None

    if not run_id:
        run_id = _discover_latest_run_via_listing()

    expiry = now + 60.0
    _LATEST_CACHE["value"] = run_id
    _LATEST_CACHE["expires"] = expiry
    return run_id


def load_manifest(run_id: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Download and cache manifest.json for a given run.
    Cache TTL: 300 seconds.
    """
    now = time.monotonic()
    expiry = _MANIFEST_EXPIRY.get(run_id, 0.0)
    if not force_refresh and now < expiry and run_id in _MANIFEST_CACHE:
        return _MANIFEST_CACHE[run_id]

    path = f"{RUNS_PREFIX}/{run_id}/manifest.json"
    manifest_bytes = download_file(path)
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    manifest.setdefault("run_id", run_id)
    _MANIFEST_CACHE[run_id] = manifest
    _MANIFEST_EXPIRY[run_id] = now + 300.0
    # Drop any cached hash lookups for this run to avoid stale data
    stale_keys = [key for key in _LOOKUP_CACHE if key[0] == run_id]
    for key in stale_keys:
        _LOOKUP_CACHE.pop(key, None)
    return manifest


def fetch_range_bytes(path_in_bucket: str, start: int, length: int, timeout: float = 10.0) -> bytes:
    """
    Perform an HTTP Range GET against Supabase public URL.
    """
    if length <= 0:
        return b""
    end = start + length - 1
    headers = {"Range": f"bytes={start}-{end}"}
    url = _get_public_url(path_in_bucket)
    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.status_code not in (200, 206):
        raise RuntimeError(
            f"Range GET failed for {path_in_bucket} ({resp.status_code}): {resp.text[:200]}"
        )
    content = resp.content
    if len(content) > length:
        content = content[:length]
    return content


def fetch_record_json(run_id: str, filename: str, offset: int, length: int) -> Dict[str, Any]:
    """
    Fetch a single JSON line using manifest-provided byte offsets.
    """
    path = f"{RUNS_PREFIX}/{run_id}/{filename}"
    raw = fetch_range_bytes(path, offset, length)
    text = raw.decode("utf-8").rstrip("\n")
    if not text:
        raise ValueError(f"No data returned for {filename} [{offset}, {length}]")
    return json.loads(text)


def _decode_hash_lookup(run_id: str, filename: str, file_entry: Dict[str, Any]) -> bytes:
    cache_key = (run_id, filename)
    if cache_key in _LOOKUP_CACHE:
        return _LOOKUP_CACHE[cache_key]

    lookup = (file_entry or {}).get("hash_lookup") or {}
    data_b64 = lookup.get("data")
    if not data_b64:
        raise ValueError(f"Manifest missing hash_lookup data for {filename}")

    encoding = lookup.get("encoding")
    if encoding not in {"zlib+base64", "base64+zlib"}:
        raise ValueError(f"Unsupported hash_lookup encoding '{encoding}' for {filename}")

    compressed = base64.b64decode(data_b64)
    buffer = zlib.decompress(compressed)

    expected_entries = lookup.get("entry_count")
    if expected_entries and len(buffer) != expected_entries * 8:
        raise ValueError(
            f"hash_lookup size mismatch for {filename}: expected {expected_entries * 8} bytes, got {len(buffer)}"
        )

    _LOOKUP_CACHE[cache_key] = buffer
    return buffer


def resolve_offset_for_location(
    run_id: str,
    filename: str,
    file_entry: Dict[str, Any],
    location_index: int,
) -> Tuple[int, int]:
    if location_index < 0:
        raise ValueError("location_index must be non-negative")

    buffer = _decode_hash_lookup(run_id, filename, file_entry)
    start = location_index * 8
    end = start + 8
    if end > len(buffer):
        raise IndexError(
            f"location_index {location_index} out of range for {filename} (buffer size {len(buffer)})"
        )

    offset, length = struct.unpack_from("<II", buffer, start)
    return int(offset), int(length)
