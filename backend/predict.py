import os
import numpy as np
from nc2h5 import convert_nc_to_h5
import h5py
import tensorflow as tf
import json
from supabase import create_client, Client
from dotenv import load_dotenv
from get_data import get_radar_data
import math
from datetime import datetime, timedelta

from model import rainnet
from utils import (
    normalize,
    denormalize,
    find_valid_sequences,
    flatten_sequences,
    get_reflectivity_data,
)


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
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return client, BUCKET_NAME_PREDICTED, BUCKET_NAME_NC

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
    model = load_model(model_path)
    predictions_2hours = predict(model, process_data[:4])
    completion_dt = datetime.now().replace(second=0, microsecond=0)
    return predictions_2hours, completion_dt

def load_model(model_path):
    model = rainnet()
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=3e-4), loss='log_cosh')
    model.load_weights(model_path)
    return model

def pred_to_json(
    predictions,
    metadata_path,
    supabase_client,
    BUCKET_NAME,
    base_time: datetime,
):
    """
    Convert predictions to JSON format suitable for raw storage.
    Filenames follow RAW_YYYYMMDD_HHMMSS based on base_time + lead minutes.
    """
    # load metadata
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

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

def pred_to_chatbot_data(
    predictions,
    locations_path,
    supabase_client,
    BUCKET_NAME,
    base_time: datetime,
):
    """
    Convert predictions to per-location chatbot JSON files.
    Filenames follow CHATBOT_YYYYMMDD_HHMMSS using base_time + lead minutes.
    """
    # load metadata
    with open(locations_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        locations = data.get("locations", [])

    if not locations:
        raise ValueError("Locations list is empty; unable to map predictions to places.")

    predicted_refl = np.asarray(predictions).squeeze()
    if predicted_refl.ndim == 2:
        # Single timestep - add leading axis for consistency
        predicted_refl = predicted_refl[np.newaxis, ...]
    if predicted_refl.ndim < 2:
        raise ValueError(f"Unexpected prediction shape: {predicted_refl.shape}")

    T = predicted_refl.shape[0]

    expected_points = len(locations)

    for t in range(T):
        lead_minutes = 5 * (t + 1)
        timestep_dt = base_time + timedelta(minutes=lead_minutes)
        ts_str = timestep_dt.strftime("%Y%m%d_%H%M%S")
        lead_label = f"+{lead_minutes}min"

        refl_slice = np.asarray(predicted_refl[t])
        refl_flat = refl_slice.reshape(-1)

        if refl_flat.size != expected_points:
            print(
                f"⚠️ Prediction timestep {t} has {refl_flat.size} grid points, "
                f"but {expected_points} locations are defined. Truncating to the shorter length."
            )

        weather_json = []
        for loc, refl_val in zip(locations, refl_flat):
            try:
                refl = round(float(np.asarray(refl_val).item()), 2)
            except (ValueError, TypeError):
                refl = float("nan")
            weather_json.append(
                {
                    "place": loc["place"],
                    "latitude": float(loc["latitude"]),
                    "longitude": float(loc["longitude"]),
                    "reflectivity": refl,
                    "rain_category": _rain_category(refl),
                }
            )

        payload = {
            "weather_data": weather_json,
        }
        json_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

        # Upload bytes directly to Supabase
        res = supabase_client.storage.from_(BUCKET_NAME).upload(
            f"CHATBOT_{ts_str}.json",
            json_bytes,
            file_options={"content-type": "application/json"},
        )

        if hasattr(res, "error") and res.error:
            print(f"❌ Upload failed for CHATBOT_{ts_str}.json: {res.error}")
        else:
            print(f"✅ Uploaded to Supabase: CHATBOT_{ts_str}.json")


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

def main():
    # Define paths and initialize Supabase
    metadata_path = "/Users/ma.angelikac.regoso/Desktop/PJDSCCHAMPION2025V2/sana_all-gorithm/backend/KCYS_metadata.json"
    model_path = "/Users/ma.angelikac.regoso/Desktop/PJDSCCHAMPION2025V2/sana_all-gorithm/backend/rainnet_FINAL4.weights.h5"
    locations_path = "/Users/ma.angelikac.regoso/Desktop/PJDSCCHAMPION2025V2/sana_all-gorithm/backend/locations.json"
    supabase_client, bucket_predicted, bucket_nc = init_supabase()
    # Clear existing files in Supabase buckets
    clear_bucket(supabase_client, bucket_predicted)
    clear_bucket(supabase_client, bucket_nc)
    # Get radar data, make predictions, and upload results
    get_radar_data(supabase_client, bucket_nc)
    input_data = get_data_from_supabase(supabase_client, bucket_nc)
    predictions_2hours, base_time = predicted_data(input_data, model_path)
    pred_to_json(
        predictions_2hours,
        metadata_path,
        supabase_client,
        bucket_predicted,
        base_time,
    )
    pred_to_chatbot_data(
        predictions_2hours,
        locations_path,
        supabase_client,
        bucket_predicted,
        base_time,
    )
    

if __name__ == "__main__":
    main()
    print("Prediction process completed.")
    
