import nexradaws
import pyart
from datetime import datetime, timedelta
import pytz
import tempfile
import matplotlib.pyplot as plt
import pyart.aux_io # ⬅️ ADDED: Import auxiliary IO module
import os          # ⬅️ ADDED: For file removal
from gridding2 import grid_radar_data
import json
from supabase import create_client, Client
import sys


# Consider using environment variables for credentials
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://xkktvmitzztjlhfyquab.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhra3R2bWl0enp0amxoZnlxdWFiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTgxODQxOCwiZXhwIjoyMDc1Mzk0NDE4fQ.H-jARxu1GjGQrmpmV3OrbogJzD7tQNNRHMg15lX6FGU")
BUCKET_NAME = "radar-data-json"
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# List all files in your Supabase bucket
files = supabase_client.storage.from_(BUCKET_NAME).list()
# Delete all files (if any exist)
if files:
    file_names = [f["name"] for f in files]
    supabase_client.storage.from_(BUCKET_NAME).remove(file_names)
    print(f"Removed {len(file_names)} files from Supabase bucket.")


# AWS connection
conn = nexradaws.NexradAwsInterface()
radar_id = 'KCYS'

mountain_timezone = pytz.timezone('US/Mountain')
now_utc = datetime.now(pytz.UTC)
start_time_utc = now_utc - timedelta(hours=2)


scans = conn.get_avail_scans_in_range(start_time_utc, now_utc, radar_id)


radar_count = 0
if scans:
    for scan in sorted(scans, key=lambda x: x.scan_time, reverse=True):
        if not scan.filename.endswith("_MDM"):
            scan = scan
            scan_time_local = scan.scan_time.astimezone(mountain_timezone)
            filename = f"{radar_id}_{scan_time_local.strftime('%Y%m%d_%H%M%S')}_V06.nc"
            with tempfile.TemporaryDirectory() as tmp_dir:
                print(f"Downloading scan to {tmp_dir} ...")
                results = conn.download([scan], tmp_dir)
                
                if results.success: # Ensure download was successful
                    # Access downloaded file correctly using .success
                    downloaded_file = results.success[0].filepath 
                    print(f"Downloaded: {downloaded_file}")
                    
                    try:
                        # ⬅️ CHANGE: Use the more robust aux_io.read_sigmet
                        radar = pyart.io.read_nexrad_archive(downloaded_file)
                        gridded_reflectivity = grid_radar_data(radar, size=(240, 240))
                        
                        # Save gridded data to a temporary NetCDF file
                        temp_grid_file = os.path.join(tmp_dir, filename)
                        pyart.io.write_grid(temp_grid_file, gridded_reflectivity)
                        print(f"Gridded data saved to {temp_grid_file}")

                        # Upload the gridded NetCDF file to Supabase
                        with open(temp_grid_file, "rb") as f:
                            response = supabase_client.storage.from_(BUCKET_NAME).upload(filename, f)

                        # Check if upload was successful
                        if hasattr(response, "error") and response.error is not None:
                            print(f"Error uploading {filename} to Supabase: {response.error}")
                        else:
                            print(f"✅ Uploaded {filename} to Supabase bucket '{BUCKET_NAME}'")
                            radar_count += 1
                            if radar_count == 4:
                                break
                    except Exception as e:
                        print(f"An error occurred while reading or processing the radar file: {e}")
                        
                    finally:
                        # ⬅️ ADDED: Explicitly remove the file to release the Windows lock
                        try:
                            os.remove(downloaded_file) 
                            print(f"Successfully removed file: {downloaded_file}")
                        except Exception as e:
                            print(f"Could not remove file for cleanup: {e}")

                else:
                    print("Download failed for the selected scan.")
        
else:
    print(f"No scans found for {radar_id}")