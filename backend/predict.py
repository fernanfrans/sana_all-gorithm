from model import rainnet
from utils import normalize, denormalize, find_valid_sequences, flatten_sequences, get_reflectivity_data
import os
import numpy as np
from nc2h5 import convert_nc_to_h5
import h5py
import tensorflow as tf
import json


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

def pred_to_json(predictions, metadata_path, output_folder):
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

        output_file = os.path.join(output_folder, f'prediction_{lead_times[t]}.json')
        with open(output_file, 'w') as outfile:
            json.dump(prediction_dict, outfile)
            print(f"Saved prediction to {output_file}")

if __name__ == "__main__":
    # input data
    input_data = "C:\\Users\\Administrator\\DATA SCIENTIST\\sana_all-gorithm\\sana_all-gorithm\\backend\\grid_data"
    model_path = "C:\\Users\\Administrator\\DATA SCIENTIST\\sana_all-gorithm\\sana_all-gorithm\\backend\\rainnet_FINAL4.weights.h5"
    output_folder = "C:\\Users\\Administrator\\DATA SCIENTIST\\sana_all-gorithm\\sana_all-gorithm\\backend\\predicted_json"
    metadata_path = "C:\\Users\\Administrator\\DATA SCIENTIST\\sana_all-gorithm\\sana_all-gorithm\\backend\\KCYS_metadata.json"
    predictions_2hours = predicted_data(input_data, model_path)
    pred_to_json(predictions_2hours, metadata_path, output_folder)
    print("Prediction process completed.")
