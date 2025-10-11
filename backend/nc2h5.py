import os
import re
import h5py
import xarray as xr

def convert_nc_to_h5(nc_files):
    """
    Convert a list of NetCDF (.nc) files to a single HDF5 file.
    """
    # If nc_files is a directory, turn it into a file list
    if isinstance(nc_files, str) and os.path.isdir(nc_files):
        nc_files = sorted(
            [os.path.join(nc_files, f) for f in os.listdir(nc_files) if f.endswith('.nc')]
        )

    if not nc_files:
        raise ValueError("No .nc files provided for conversion.")

    # Create output file in same folder as the first .nc file
    first_dir = os.path.dirname(nc_files[0])
    output_h5_file = os.path.join(first_dir, 'data.h5')

    with h5py.File(output_h5_file, 'w') as h5f:
        for file_path in sorted(nc_files):
            nc_file = os.path.basename(file_path)
            match = re.search(r'(\d{8})_(\d{6})', nc_file)
            dataset_name = match.group(1) + "_" + match.group(2) if match else os.path.splitext(nc_file)[0]

            try:
                ds = xr.open_dataset(file_path)
                if "reflectivity" in ds.data_vars:
                    reflectivity_data = ds['reflectivity'].values
                    h5f.create_dataset(dataset_name, data=reflectivity_data, compression='gzip')
                else:
                    print(f"⚠️ Warning: 'reflectivity' variable not found in {nc_file}. Skipping.")
                ds.close()
            except Exception as e:
                print(f"❌ Error processing {nc_file}: {e}")

    print(f"✅ HDF5 file saved as {output_h5_file}")
    return output_h5_file
