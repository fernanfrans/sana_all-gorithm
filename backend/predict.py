from model import rainnet
from utils import normalize, denormalize, find_valid_sequences, flatten_sequences, get_reflectivity_data
import os
import numpy as np
from nc2h5 import convert_nc_to_h5
import h5py
import tensorflow as tf
import json
from supabase import create_client, Client
import io
from dotenv import load_dotenv
from get_data import get_radar_data


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
    """
    process_data = dataset(input_data)
    model = load_model(model_path)
    predictions_2hours = predict(model, process_data[:4])
    return predictions_2hours

def load_model(model_path):
    model = rainnet()
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=3e-4), loss='log_cosh')
    model.load_weights(model_path)
    return model

def pred_to_json(predictions, metadata_path, supabase_client, BUCKET_NAME):
    """
    Convert predictions to JSON format.
    """
    # load metadata
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    print(metadata.keys())
    predicted_refl = np.array(predictions)
    T = predicted_refl.shape[0]

    lead_times = [f'+{5*i}min' for i in range(1, 25)]
    for t in range(T):
        prediction_dict = {
            "metadata": {
                "variable": "reflectivity_predicted",
                "units": "dBZ",
                "origin_latitude": metadata["metadata"]["origin_latitude"],
                "origin_longitude": metadata["metadata"]["origin_longitude"],
                "projection": metadata["metadata"]["projection"],
                "shape": predicted_refl[t].shape,
                "lead_time": lead_times[t]
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
            f'tryprediction_{lead_times[t]}.json',
            json_bytes,
            file_options={"content-type": "application/json"}
        )

        if hasattr(res, 'error') and res.error:
            print(f"❌ Upload failed for prediction_{lead_times[t]}.json: {res.error}")
        else:
            print(f"✅ Uploaded to Supabase: prediction_{lead_times[t]}.json")

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
    metadata_path = "C:\\Users\\Administrator\\DATA SCIENTIST\\sana_all-gorithm\\sana_all-gorithm\\backend\\KCYS_metadata.json"
    model_path = "C:\\Users\\Administrator\\DATA SCIENTIST\\sana_all-gorithm\\sana_all-gorithm\\backend\\rainnet_FINAL4.weights.h5"
    supabase_client, bucket_predicted, bucket_nc = init_supabase()
    # Clear existing files in Supabase buckets
    clear_bucket(supabase_client, bucket_predicted)
    clear_bucket(supabase_client, bucket_nc)
    # Get radar data, make predictions, and upload results
    get_radar_data(supabase_client, bucket_nc)
    input_data = get_data_from_supabase(supabase_client, bucket_nc)
    predictions_2hours = predicted_data(input_data, model_path)
    pred_to_json(predictions_2hours, metadata_path, supabase_client, bucket_predicted)
    


if __name__ == "__main__":
    main()
    print("Prediction process completed.")
    
