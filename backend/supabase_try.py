from supabase import create_client
import json 
import os

SUPABASE_URL = "https://xkktvmitzztjlhfyquab.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhra3R2bWl0enp0amxoZnlxdWFiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTgxODQxOCwiZXhwIjoyMDc1Mzk0NDE4fQ.H-jARxu1GjGQrmpmV3OrbogJzD7tQNNRHMg15lX6FGU"
BUCKET_NAME = "radar-data-json"
 
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_to_supabase(file_path, bucket_name=BUCKET_NAME):
    file_name = os.path.basename(file_path)
    with open(file_path, "rb") as file:
        try:
            supabase.storage.from_(bucket_name).upload(file_name, file)
        except:
            file.seek(0)
            supabase.storage.from_(bucket_name).update(file_name, file)
    print(f"Successfully uploaded {file_name} to bucket {bucket_name}")

def read_from_supabase(file_name, bucket_name=BUCKET_NAME):
    res = supabase.storage.from_(bucket_name).list()
    print("Files in bucket:", res)

if __name__ == "__main__":
    local_file_path = "C:\\Users\\Administrator\\DATA SCIENTIST\\sana_all-gorithm\\sana_all-gorithm\\backend\\KCYS_metadata.json"
    upload_to_supabase(local_file_path)
    # Example reading the file back
    file_name = os.path.basename(local_file_path)
    read_from_supabase(file_name)
    
