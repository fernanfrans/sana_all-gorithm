from datetime import datetime, timedelta
import nexradaws
import pytz

# Instantiate the interface
conn = nexradaws.NexradAwsInterface()

# Radar ID
radar_id = 'KCYS'
mountain_timezone = pytz.timezone('US/Mountain')

# Current time in radar's timezone
now = datetime.now(mountain_timezone)

# Look back a few hours
start_time = now - timedelta(hours=6)
end_time = now

# Fetch scans
scans = conn.get_avail_scans_in_range(start_time, end_time, radar_id)

if scans:
    # Sort scans by scan_time descending
    scans_sorted = sorted(scans, key=lambda x: x.scan_time, reverse=True)

    # Take the last 5 scans
    last_5_scans = scans_sorted[:5]

    for scan in last_5_scans:
        # Convert scan time to Mountain Time
        scan_time_mountain = scan.scan_time.astimezone(mountain_timezone)

        # Generate a filename based on Mountain Time
        filename = f"{radar_id}{scan_time_mountain.strftime('%Y%m%d_%H%M%S')}_V06"
        print(filename)
else:
    print("No scans available in the last 6 hours.")
