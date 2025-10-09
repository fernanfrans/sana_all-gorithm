import nexradaws
import pyart
from datetime import datetime, timedelta
import pytz
import tempfile
import matplotlib.pyplot as plt
import pyart.aux_io # ⬅️ ADDED: Import auxiliary IO module
import os          # ⬅️ ADDED: For file removal

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
                        
                        # Example: reflectivity
                        reflectivity = radar.fields['reflectivity']['data']
                        print(f"Reflectivity shape: {reflectivity.shape}, range: {reflectivity.min()} to {reflectivity.max()}")
                        radar_altitude = radar.altitude['data'][0]
                        print(f"Radar altitude: {radar_altitude} meters")
                        radar_count += 1
                        if radar_count == 1:
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