from datetime import datetime, timedelta
import nexradaws
import pyart
import pytz
import tempfile
import os
from supabase import create_client, Client

# Consider using environment variables for credentials
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://xkktvmitzztjlhfyquab.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhra3R2bWl0enp0amxoZnlxdWFiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTgxODQxOCwiZXhwIjoyMDc1Mzk0NDE4fQ.H-jARxu1GjGQrmpmV3OrbogJzD7tQNNRHMg15lX6FGU")
BUCKET_NAME = "radar-data-json"
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_radar_data_temp():
    """Fetch 2 latest NEXRAD radar scans and upload to Supabase without permanent download."""
    conn = nexradaws.NexradAwsInterface()
    radar_id = 'KCYS'

    mountain_timezone = pytz.timezone('US/Mountain')
    now_utc = datetime.now(pytz.UTC)  # Use UTC for API calls
    start_time_utc = now_utc - timedelta(hours=2)

    scans = conn.get_avail_scans_in_range(start_time_utc, now_utc, radar_id)
    radar_count = 0

    if scans:
        for scan in sorted(scans, key=lambda x: x.scan_time, reverse=True):
            try:
                if not scan.filename.endswith("_MDM"):
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        # Download to temporary directory
                        downloads = conn.download([scan], tmp_dir)
                        
                        # Get the downloaded file path (it's in the temp directory)
                        local_file_path = os.path.join(tmp_dir, scan.filename) 

                        # Convert scan time to Mountain timezone for filename
                        scan_time_mountain = scan.scan_time.astimezone(mountain_timezone)
                        
                        # Preserve original file extension
                        original_ext = os.path.splitext(scan.filename)[1]
                        filename = f"{radar_id}_{scan_time_mountain.strftime('%Y%m%d_%H%M%S')}_V06{original_ext}"

                        # Check if file already exists
                        try:
                            existing_files = supabase_client.storage.from_(BUCKET_NAME).list()
                            file_exists = any(f['name'] == filename for f in existing_files)
                            
                            if file_exists:
                                print(f"⏭️  Skipping (already exists): {filename}")
                                radar_count += 1
                                if radar_count == 2:
                                    break
                                continue
                        except Exception as e:
                            print(f"⚠️  Could not check existing files: {e}")

                        # Upload to Supabase
                        with open(local_file_path, "rb") as f:
                            res = supabase_client.storage.from_(BUCKET_NAME).upload(
                                filename, 
                                f,
                                file_options={"content-type": "application/octet-stream"}
                            )
                            
                            # Check for upload errors
                            if hasattr(res, 'error') and res.error:
                                print(f"❌ Upload failed for {filename}: {res.error}")
                            else:
                                print(f"✅ Uploaded to Supabase: {filename}")

                    radar_count += 1
                    if radar_count == 2:
                        break
            except Exception as e:
                print(f"⚠️  Skipping {scan.filename}: {e}")
    else:
        print("No scans available in the last 2 hours.")

if __name__ == "__main__":
    get_radar_data_temp()
    print("Radar data processing complete.")