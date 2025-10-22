import os
import tempfile
from datetime import datetime, timedelta
import pytz
import nexradaws
import pyart
from dotenv import load_dotenv
from supabase import create_client, Client
from gridding import grid_radar_data



# ----------------------------
# NEXRAD AWS Radar Processing
# ----------------------------
def get_recent_scans(radar_id: str, hours_back: int = 12):
    conn = nexradaws.NexradAwsInterface()
    now_utc = datetime.now(pytz.UTC)
    start_time_utc = now_utc - timedelta(hours=hours_back)
    scans = conn.get_avail_scans_in_range(start_time_utc, now_utc, radar_id)
    return conn, scans


def process_and_upload_scan(conn, scan, radar_id, supabase_client, bucket_name, mountain_timezone):
    scan_time_local = scan.scan_time.astimezone(mountain_timezone)
    filename = f"{radar_id}_{scan_time_local.strftime('%Y%m%d_%H%M%S')}_V06.nc"

    with tempfile.TemporaryDirectory() as tmp_dir:
        print(f"📥 Downloading scan to {tmp_dir} ...")
        results = conn.download([scan], tmp_dir)

        if not results.success:
            print("❌ Download failed for this scan.")
            return False

        downloaded_file = results.success[0].filepath
        print(f"Downloaded: {downloaded_file}")

        try:
            radar = pyart.io.read_nexrad_archive(downloaded_file)
            gridded_reflectivity = grid_radar_data(radar, size=(240, 240))

            # Save gridded data to temporary NetCDF
            temp_grid_file = os.path.join(tmp_dir, filename)
            pyart.io.write_grid(temp_grid_file, gridded_reflectivity)
            print(f"✅ Gridded data saved to {temp_grid_file}")

            # Upload to Supabase
            with open(temp_grid_file, "rb") as f:
                response = supabase_client.storage.from_(bucket_name).upload(filename, f)

            if hasattr(response, "error") and response.error is not None:
                print(f"⚠️ Upload error for {filename}: {response.error}")
                return False

            print(f"✅ Uploaded {filename} to Supabase bucket '{bucket_name}'")
            return True

        except Exception as e:
            print(f"⚠️ Error processing radar file: {e}")
            return False

        finally:
            try:
                os.remove(downloaded_file)
                print(f"🧹 Removed local file: {downloaded_file}")
            except Exception as e:
                print(f"⚠️ Cleanup failed: {e}")


# ----------------------------
# Main execution flow
# ----------------------------
def get_radar_data(supabase_client, bucket_name):
    radar_id = 'KCYS'
    mountain_timezone = pytz.timezone('US/Mountain')

    # Get recent radar scans
    conn, scans = get_recent_scans(radar_id, hours_back=2)

    if not scans:
        print(f"No scans found for {radar_id}")
        return

    radar_count = 0
    for scan in sorted(scans, key=lambda x: x.scan_time, reverse=True):
        if scan.filename.endswith("_MDM"):
            continue

        success = process_and_upload_scan(conn, scan, radar_id, supabase_client, bucket_name, mountain_timezone)
        if success:
            radar_count += 1
        if radar_count == 4:
            break

    print(f"🎯 Finished processing {radar_count} radar scans.")


# ----------------------------
# Entry point
# ----------------------------
if __name__ == "__main__":
    get_radar_data()
