import re
import numpy as np
from datetime import datetime
from scipy.ndimage import uniform_filter


# scale data
def scaler(data):
    return np.log(data+0.01)

# inverse scale data
def inverse_scaler(data):
    return np.exp(data)-0.01

# normalize input data
def normalize(X):
    X = np.moveaxis(X, 0, -1)
    X = X[np.newaxis, ::, ::, ::]
    X = scaler(X)
    return X

# denormalize output data
def denormalize(preds):
    preds_array = np.squeeze(np.array(preds))
    scaled_preds = inverse_scaler(preds_array)
    clipped_preds = np.where(scaled_preds > 0, scaled_preds, 0)
    return clipped_preds

# extract timestamp from data key
def extract_timestamp(key):
    match = re.search(r'(\d{8})_(\d{4})', key)
    if match:
        date_str = match.group(1)
        time_str = match.group(2)
        return datetime.strptime(date_str + time_str, '%Y%m%d%H%M')
    else:
        raise None

# find valid sequences of data keys  
def find_valid_sequences(keys):
    keys_with_timestamps = []

    for key in keys:
        try: 
            time = extract_timestamp(key)
            if time:
                keys_with_timestamps.append((key, time))
        except:
            continue
    keys_with_timestamps.sort(key=lambda x: x[1])

    valid_sequences = []
    for i in range(len(keys_with_timestamps) - 3):
        group = keys_with_timestamps[i:i + 4]
        times = [t for _, t in group]

        intervals = []
        for j in range(3):
            difference = times[j + 1] - times[j]
            seconds = difference.total_seconds()
            minutes = seconds / 60
            intervals.append(minutes)
        
        if all(9 <= dt <= 12 for dt in intervals):
            valid_sequences.append([key for key, _ in group])

    return valid_sequences

# flatten the valid sequences
def flatten_sequences(sequences):
    flat_list = []
    seen = set()
    for seq in sequences:
        for item in seq:
            if item not in seen:
                seen.add(item)
                flat_list.append(item)
    return flat_list

# getting reflectivity data from the dataset
def get_reflectivity_data(dataset_dict, flat_list):
    reflectivity_data = []
    for key in flat_list:
        if key in dataset_dict:
            reflectivity_data.append(dataset_dict[key])
        else:
            raise KeyError(f"Key {key} not found in the dataset.")
    reflectivity_data = np.array(reflectivity_data).squeeze()
    return reflectivity_data