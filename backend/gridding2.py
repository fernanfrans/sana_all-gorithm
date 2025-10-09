from matplotlib import pyplot as plt
import pyart
import numpy as np
import os
from datetime import datetime


def grid_radar_data(radar, size):
    """Grid radar reflectivity data and save to NetCDF."""
    radar_altitude = radar.altitude['data'][0]

    # Grid radar data to a uniform 2D array
    grids = pyart.map.grid_from_radars(
        radar,
        grid_shape=(1, size[0], size[1]),
        grid_limits=((2000 - radar_altitude, 2000 - radar_altitude),
                     (-119500, 119500), (-119500, 119500)),
        fields=['reflectivity'],
        gridding_algo='map_gates_to_grid',
        weighting_function='BARNES2'
    )

    # Extract reflectivity
    img_mtx = grids.fields['reflectivity']['data'][0, :, :]
    img_mtx = np.clip(img_mtx, 0, 75)
    img_mtx = np.ma.filled(img_mtx, fill_value=0).astype(np.uint8)

    grids.fields['reflectivity']['data'][0, :, :] = img_mtx

    # # Save the gridded data
    # pyart.io.write_grid(output_file, grids)
    # print(f"✅ Gridded data saved to {output_file}")

    return img_mtx

def process_radar_files(radar, filename, size):
    """Process multiple radar scans and grid each one."""
    try:
        radar_grid = grid_radar_data(radar, size)
        print(f"  ✓ Gridded to shape {radar_grid.shape}")
        return {
            'filename': filename,
            'grid': radar_grid
        }

    except Exception as e:
        print(f"⚠️ Error processing {radar}: {e}")
        return None

    
