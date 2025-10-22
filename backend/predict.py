from model import rainnet
import base64
from utils import normalize, denormalize, find_valid_sequences, flatten_sequences, get_reflectivity_data
import os
import json
import math
import hashlib
import re
import struct
import zlib
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import h5py
import numpy as np
from nc2h5 import convert_nc_to_h5
import h5py
import tensorflow as tf
from dotenv import load_dotenv
from get_data import get_radar_data
from supabase import create_client, Client


# ----------------------------
# Environment & Supabase Setup
# ----------------------------
def init_supabase():
    dotenv_path = os.path.join(os.path.dirname(__file__), '../config/.env.example')
    load_dotenv(dotenv_path)
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    BUCKET_NAME_PREDICTED = os.getenv("BUCKET_PREDICTED")
    BUCKET_NAME_NC = os.getenv("BUCKET_NC")
    BUCKET_NAME_METADATA = os.getenv("BUCKET_METADATA")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return client, BUCKET_NAME_PREDICTED, BUCKET_NAME_NC, BUCKET_NAME_METADATA


def normalize_place_name(name: str) -> str:
    """
    Convert a place string into a stable, URL-safe slug.
    Ensures the result is non-empty by falling back to 'unknown'.
    """
    base = (name or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", base)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "unknown"

def clear_bucket(supabase_client: Client, bucket_name: str):
    files = supabase_client.storage.from_(bucket_name).list()
    if files:
        file_names = [f["name"] for f in files]
        supabase_client.storage.from_(bucket_name).remove(file_names)
        print(f"Removed {len(file_names)} files from Supabase bucket.")
    else:
        print("No files found in Supabase bucket.")

def predict(model, input_data):
    """
    Predict reflectivity data for the next 120 mins of reflectivity data.
    """
    predictions = []
    window = input_data.copy()

    for i in range(24):
        normalized_window = normalize(window)
        pred = model.predict(normalized_window)
        denorm_pred = denormalize(pred)
        predictions.append(denorm_pred)
        window = np.concatenate([window[1:], np.expand_dims(denorm_pred, axis=0)], axis=0)
    
    return predictions

def dataset(input_data):
    """
    Process the input data and return valid sequences.
    """
    # Convert NetCDF files to HDF5
    radar_h5 = convert_nc_to_h5(input_data)
    # Load the HDF5 file
    with h5py.File(radar_h5, 'r') as dataset_dict:
        radar_keys = list(dataset_dict.keys())
        valid_sequences = find_valid_sequences(radar_keys)
        if not valid_sequences:
            raise ValueError("No valid sequences found in the dataset.")
        else:
            flat_list = flatten_sequences(valid_sequences)
            reflectivity_data = get_reflectivity_data(dataset_dict, flat_list)
            return reflectivity_data


def predicted_data(input_data, model_path):
    """
    Get the predicted reflectivity data for the next 120 mins.
    Returns (predictions, completion_datetime_truncated_to_minute).
    """
    process_data = dataset(input_data)
    if len(process_data) < 4:
        raise ValueError("Insufficient input frames to seed prediction model (need >= 4).")
    model = load_model(model_path)
    predictions_2hours = predict(model, process_data[:4])
    completion_dt = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    latest_observation = np.asarray(process_data[3])
    return predictions_2hours, completion_dt, latest_observation

def load_model(model_path):
    model = rainnet()
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=3e-4), loss='log_cosh')
    model.load_weights(model_path)
    return model

def pred_to_json(predictions, metadata, supabase_client, BUCKET_NAME, base_time: datetime):
    """
    Convert predictions to JSON format suitable for raw storage.
    Filenames follow RAW_YYYYMMDD_HHMMSS based on base_time + lead minutes.
    """
    
    print(metadata.keys())
    predicted_refl = np.array(predictions)
    T = predicted_refl.shape[0]

    for t in range(T):
        lead_minutes = 5 * (t + 1)
        timestep_dt = base_time + timedelta(minutes=lead_minutes)
        ts_str = timestep_dt.strftime("%Y%m%d_%H%M%S")
        lead_label = f"+{lead_minutes}min"
        prediction_dict = {
            "metadata": {
                "variable": "reflectivity_predicted",
                "units": "dBZ",
                "origin_latitude": metadata["metadata"]["origin_latitude"],
                "origin_longitude": metadata["metadata"]["origin_longitude"],
                "projection": metadata["metadata"]["projection"],
                "shape": predicted_refl[t].shape,
                "lead_time": lead_label,
                "valid_datetime": timestep_dt.isoformat()
            },
            "coordinates": {
                "lat": metadata["coordinates"]["lat"],
                "lon": metadata["coordinates"]["lon"]
            },
            "reflectivity": predicted_refl[t].tolist()
        }

        # Convert JSON dict to bytes
        json_bytes = json.dumps(prediction_dict).encode('utf-8')

        # Upload bytes directly to Supabase
        res = supabase_client.storage.from_(BUCKET_NAME).upload(
            f'RAW_{ts_str}.json',
            json_bytes,
            file_options={"content-type": "application/json"}
        )

        if hasattr(res, 'error') and res.error:
            print(f"❌ Upload failed for RAW_{ts_str}.json: {res.error}")
        else:
            print(f"✅ Uploaded to Supabase: RAW_{ts_str}.json")

def _rain_category(dbz: float) -> str:
    """
    Categorize reflectivity (dBZ) using your table:
      0 to 20   -> Very light
      20 to 40  -> Light
      40 to 50  -> Moderate
      50 to 65  -> Heavy
      >65    -> Extremely heavy
    """
    if dbz is None or (isinstance(dbz, float) and math.isnan(dbz)):
        return "Unknown"
    if dbz > 65:
        return "Extremely heavy"
    if dbz >= 50:
        return "Heavy"
    if dbz >= 40:
        return "Moderate"
    if dbz >= 20:
        return "Light"
    return "Very light"


def _prepare_locations(locations: List[Dict[str, float]]) -> List[Dict[str, object]]:
    """
    Prepare location metadata with unique normalized_place keys.
    """
    prepared: List[Dict[str, object]] = []
    slug_counts: Dict[str, int] = {}
    for idx, loc in enumerate(locations):
        place = loc.get("place") or f"location-{idx}"
        base_slug = normalize_place_name(place)
        count = slug_counts.get(base_slug, 0)
        slug = base_slug if count == 0 else f"{base_slug}-{count}"
        slug_counts[base_slug] = count + 1
        prepared.append(
            {
                "place": place,
                "normalized_place": slug,
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "index": idx,
            }
        )
    return prepared


def _safe_reflectivity(value) -> Optional[float]:
    """
    Convert arbitrary input into a rounded float or None.
    Ensures JSON encoding remains standards-compliant (no NaN).
    """
    try:
        scalar = float(np.asarray(value).item())
    except (ValueError, TypeError):
        return None
    if math.isnan(scalar):
        return None
    return round(scalar, 2)


def _build_records_for_slice(
    slice_data: np.ndarray,
    *,
    lead_minutes: int,
    valid_dt: datetime,
    run_id: str,
    locations: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    """
    Flatten one prediction slice into per-location records.
    """
    flat = np.asarray(slice_data).reshape(-1)
    expected = len(locations)
    if flat.size < expected:
        print(
            f"⚠️ Prediction slice has {flat.size} points, "
            f"but {expected} locations defined. Truncating."
        )
    trimmed = flat[:expected]
    records: List[Dict[str, object]] = []
    for loc, refl_val in zip(locations, trimmed):
        refl = _safe_reflectivity(refl_val)
        records.append(
            {
                "run_id": run_id,
                "place": loc["place"],
                "normalized_place": loc["normalized_place"],
                "location_index": loc["index"],
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
                "lead_minutes": lead_minutes,
                "valid_datetime": valid_dt.isoformat(),
                "reflectivity": refl,
                "rain_category": _rain_category(refl),
            }
        )
    return records


def _encode_records_to_jsonl(records: List[Dict[str, object]]) -> Tuple[bytes, List[Tuple[int, int]]]:
    """
    Encode records into UTF-8 JSON Lines and capture byte offsets per record.
    Returns the concatenated JSONL bytes and an ordered list of (offset, length)
    aligned with the input record order.
    """
    buffer = BytesIO()
    offsets: List[Tuple[int, int]] = []
    cursor = 0
    for record in records:
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        data = line.encode("utf-8") + b"\n"
        buffer.write(data)
        offsets.append((cursor, len(data)))
        cursor += len(data)
    return buffer.getvalue(), offsets


def _compress_offsets(offsets: List[Tuple[int, int]]) -> Dict[str, object]:
    """
    Pack (offset,length) pairs as little-endian uint32 tuples, compress with zlib,
    and base64 encode for manifest storage.
    """
    packed = bytearray()
    for start, length in offsets:
        if start < 0 or length < 0:
            raise ValueError("Offsets must be non-negative")
        packed.extend(struct.pack("<II", int(start), int(length)))

    compressed = zlib.compress(bytes(packed), level=9)
    encoded = base64.b64encode(compressed).decode("ascii")
    return {
        "encoding": "zlib+base64",
        "format": "uint32-le",
        "entry_count": len(offsets),
        "data": encoded,
        "packed_bytes": len(packed),
        "compressed_bytes": len(compressed),
    }

def pred_to_chatbot_data(
    predictions,
    latest_observation,
    locations_path,
    supabase_client,
    BUCKET_NAME,
    base_time: datetime,
):
    """
    Convert predictions to per-location chatbot JSON files.
    Filenames follow CHATBOT_YYYYMMDD_HHMMSS using base_time + lead minutes.
    """
    
    locations = locations_path.get("locations", [])

    if not locations:
        raise ValueError("Locations list is empty; unable to map predictions to places.")

    prepared_locations = _prepare_locations(locations)

    predicted_refl = np.asarray(predictions).squeeze()
    if predicted_refl.ndim == 2:
        predicted_refl = predicted_refl[np.newaxis, ...]
    if predicted_refl.ndim != 3:
        raise ValueError(f"Unexpected prediction shape: {predicted_refl.shape}")

    latest_obs_arr = np.asarray(latest_observation).squeeze()
    if latest_obs_arr.ndim != 2:
        # Attempt to reshape using prediction spatial dimensions
        latest_obs_arr = latest_obs_arr.reshape(predicted_refl.shape[1], predicted_refl.shape[2])

    base_time = base_time if base_time.tzinfo else base_time.replace(tzinfo=timezone.utc)
    base_time_utc = base_time.astimezone(timezone.utc)
    run_id = base_time_utc.strftime("%Y%m%dT%H%MZ")

    lead_minutes_values: List[int] = [0] + [5 * (idx + 1) for idx in range(predicted_refl.shape[0])]
    slices = [latest_obs_arr] + [predicted_refl[idx] for idx in range(predicted_refl.shape[0])]

    lead_files: List[Dict[str, object]] = []
    manifest_files: Dict[str, Dict[str, object]] = {}

    for lead_minutes, slice_data in zip(lead_minutes_values, slices):
        valid_dt = base_time_utc + timedelta(minutes=lead_minutes)
        records = _build_records_for_slice(
            slice_data,
            lead_minutes=lead_minutes,
            valid_dt=valid_dt,
            run_id=run_id,
            locations=prepared_locations,
        )
        file_bytes, offsets = _encode_records_to_jsonl(records)
        compressed_lookup = _compress_offsets(offsets)
        filename = f"lead_{lead_minutes:03d}.jsonl"
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        file_size = len(file_bytes)

        lead_files.append(
            {
                "name": filename,
                "bytes": file_bytes,
                "sha256": file_hash,
                "size": file_size,
                "entry_count": len(offsets),
                "lookup": compressed_lookup,
            }
        )
        manifest_files[filename] = {
            "sha256": file_hash,
            "size": file_size,
            "entry_count": len(offsets),
            "hash_lookup": compressed_lookup,
        }

    manifest = {
        "run_id": run_id,
        "base_time": base_time_utc.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lead_bins": lead_minutes_values,
        "files": manifest_files,
        "locations": [
            {
                "place": loc["place"],
                "normalized_place": loc["normalized_place"],
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
                "location_index": loc["index"],
            }
            for loc in prepared_locations
        ],
    }

    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    manifest_path = f"runs/{run_id}/manifest.json"

    storage = supabase_client.storage.from_(BUCKET_NAME)
    try:
        existing_runs = storage.list("runs")
    except Exception as exc:
        existing_runs = []
        print(f"⚠️ Unable to list existing run folders: {exc}")

    stale_runs = [entry.get("name") for entry in existing_runs or [] if entry.get("name")]
    removed_total = 0
    for run_name in stale_runs:
        normalized = run_name.rstrip("/")
        try:
            run_items = storage.list(f"runs/{normalized}")
        except Exception:
            run_items = []
        paths = [
            f"runs/{normalized}/{item.get('name')}"
            for item in (run_items or [])
            if item.get("name")
        ]
        if paths:
            storage.remove(paths)
            removed_total += len(paths)
    if removed_total:
        print(f"🗑️ Removed {removed_total} previous run object(s).")

    run_prefix = f"runs/{run_id}/"

    print(f"📦 Publishing chatbot run {run_id} with {len(lead_files)} lead files…")
    for lead_file in lead_files:
        path = f"{run_prefix}{lead_file['name']}"
        res = storage.upload(
            path,
            lead_file["bytes"],
            file_options={
                "content-type": "application/x-ndjson",
                "upsert": "true",
            },
        )
        if hasattr(res, "error") and res.error:
            raise RuntimeError(f"Upload failed for {path}: {res.error}")
        print(f"  ✅ Uploaded {path} ({lead_file['size']} bytes)")

    res_manifest = storage.upload(
        manifest_path,
        manifest_bytes,
        file_options={
            "content-type": "application/json",
            "upsert": "true",
        },
    )
    if hasattr(res_manifest, "error") and res_manifest.error:
        raise RuntimeError(f"Upload failed for {manifest_path}: {res_manifest.error}")
    print(f"  ✅ Uploaded {manifest_path}")

    latest_bytes = f"{run_id}\n".encode("utf-8")
    latest_res = storage.upload(
        "latest.txt",
        latest_bytes,
        file_options={
            "content-type": "text/plain",
            "upsert": "true",
        },
    )
    if hasattr(latest_res, "error") and latest_res.error:
        raise RuntimeError(f"Upload failed for latest.txt: {latest_res.error}")
    print("  ✅ Updated latest.txt")


def get_data_from_supabase(supabase_client, BUCKET_NAME):
    """
    Download NetCDF files from Supabase bucket.
    """
    try:
        files = supabase_client.storage.from_(BUCKET_NAME).list()
        if not files:
            raise ValueError("No files found in the specified Supabase bucket.")
        
        sorted_files = sorted([f['name'] for f in files])
        local_files = []
        for f_name in sorted_files:
            data = supabase_client.storage.from_(BUCKET_NAME).download(f_name)
            local_path = os.path.join("downloaded_nc_files", f_name)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(data)
            local_files.append(local_path)
        return local_files
    except Exception as e:
        print(f"Error downloading files from Supabase: {e}")
        return None

def get_file_from_supabase(supabase_client, BUCKET_NAME, filename):
    """
    Download metadata JSON file from Supabase bucket.
    """
    try:
        data = supabase_client.storage.from_(BUCKET_NAME).download(filename)
        file = json.loads(data.decode('utf-8'))
        return file
    except Exception as e:
        print(f"Error downloading metadata from Supabase: {e}")
        return None

def predict_main():
    # Define paths and initialize Supabase
    supabase_client, bucket_predicted, bucket_nc, bucket_meta = init_supabase()
    metadata = get_file_from_supabase(supabase_client, bucket_meta, "KCYS_metadata.json")
    locations = get_file_from_supabase(supabase_client, bucket_meta, "locations.json")
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(ROOT_DIR, "backend", "rainnet_FINAL4.weights.h5")

    # # Clear existing files in Supabase buckets
    # clear_bucket(supabase_client, bucket_predicted)
    # Clear existing NetCDF inputs before downloading new radar data
    clear_bucket(supabase_client, bucket_nc)
    # Get radar data, make predictions, and upload results
    print("Starting radar data retrieval...")
    get_radar_data(supabase_client, bucket_nc)
    print("Radar data retrieval completed.")
    input_data = get_data_from_supabase(supabase_client, bucket_nc)
    predictions_2hours, base_time, latest_observation = predicted_data(input_data, model_path)
    pred_to_json(
        predictions_2hours,
        metadata,
        supabase_client,
        bucket_predicted,
        base_time,
    )
    pred_to_chatbot_data(
        predictions_2hours,
        latest_observation,
        locations,
        supabase_client,
        bucket_predicted,
        base_time,
    )

    return True


if __name__ == "__main__":
    predict_main()
    print("Prediction process completed.")
    
