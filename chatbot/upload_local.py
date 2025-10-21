import argparse
import os
import mimetypes
from pathlib import Path
from chatbot.supabase_client import get_client

BUCKET = "radar-predicted"

def guess_content_type(path: Path) -> str:
    ctype, _ = mimetypes.guess_type(str(path))
    # Default to JSON for .json, otherwise binary stream
    if path.suffix.lower() == ".json":
        return "application/json"
    return ctype or "application/octet-stream"

def main():
    parser = argparse.ArgumentParser(description="Upload local files to Supabase Storage")
    parser.add_argument("--src", required=True, help="Local source directory with files")
    parser.add_argument("--prefix", default="", help="Prefix inside bucket, e.g. 'samples/'")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be uploaded without doing it")
    parser.add_argument("--upsert", action="store_true", help="Overwrite if file exists (default: no)")
    args = parser.parse_args()

    src_root = Path(args.src).resolve()
    if not src_root.exists() or not src_root.is_dir():
        raise SystemExit(f"Source directory not found: {src_root}")

    sb = get_client()
    files = [p for p in src_root.rglob("*") if p.is_file()]

    if not files:
        print("No files found.")
        return

    print(f"Found {len(files)} file(s). Starting upload...\n")
    successes = 0
    for f in files:
        rel = f.relative_to(src_root).as_posix()
        dest_path = f"{args.prefix}{rel}" if args.prefix else rel
        content_type = guess_content_type(f)
        data = f.read_bytes()

        print(f"→ {f}  ==>  {dest_path}  [{content_type}]")
        if args.dry_run:
            continue

        res = sb.storage.from_(BUCKET).upload(
            dest_path,
            data,
            {
                "contentType": content_type,
                "upsert": "true" if args.upsert else "false",
            },
        )

        # Get a public URL if your bucket is Public (as we set up)
        url = sb.storage.from_(BUCKET).get_public_url(dest_path)
        print(f"   Uploaded ✓  {url}\n")
        successes += 1

    if args.dry_run:
        print("\n(DRY RUN) No files were uploaded.")
    else:
        print(f"\nDone. Uploaded {successes}/{len(files)} file(s).")

if __name__ == "__main__":
    main()
