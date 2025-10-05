import os 
import re
import h5py 
import xarray as xr

def convert_nc_to_h5(nc_dir):
    output_h5_file = os.path.join(nc_dir, 'data.h5')
    with h5py.File(output_h5_file, 'w') as h5f:
        nc_files = sorted([f for f in os.listdir(nc_dir) if f.endswith('.nc')])
        for nc_file in nc_files:
            file_path = os.path.join(nc_dir, nc_file)
            match = re.search(r'(\d{8})_(\d{6})', nc_file)
            dataset_name = match.group(1) + "_" + match.group(2) if match else os.path.splitext(nc_file)[0]
            try:
                ds = xr.open_dataset(file_path)
                if "reflectivity" in ds.data_vars:
                    reflectivity_data = ds['reflectivity'].values
                    h5f.create_dataset(dataset_name, data=reflectivity_data, compression='gzip')
                    # print(f"Converted {nc_file} to HDF5 dataset '{dataset_name}'")
                else:
                    continue
                    # print(f"Warning: 'reflectivity' variable not found in {nc_file}. Skipping.")
                ds.close()
            except Exception as e:
                print(f"Error processing {nc_file}: {e}")
    # print(f'HDF5 file saved as {output_h5_file}')
    return output_h5_file


