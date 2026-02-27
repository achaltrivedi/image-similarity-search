import os
import sys
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from core.preprocessor import ImagePreprocessor
from utils.minio_utils import SUPPORTED_IMAGE_EXTENSIONS, list_all_objects, download_object, upload_object, object_exists
from utils.minio_config import BUCKET_NAME

def backfill_thumbnails():
    print("=" * 60)
    print("🎨 BACKFILLING MISSING THUMBNAILS")
    print("=" * 60)
    
    # Files that need thumbnails
    target_exts = (".ai", ".pdf")
    
    processed = 0
    generated = 0
    skipped = 0
    errors = 0

    try:
        for obj in list_all_objects():
            key = obj.object_name
            
            # Skip thumbnails themselves
            if key.startswith(".thumbnails/"):
                continue
                
            # Only check likely targets (AI/PDF)
            if not key.lower().endswith(target_exts):
                continue

            processed += 1
            thumb_key = f".thumbnails/{key}.png"
            
            # Check if thumbnail exists
            if object_exists(thumb_key):
                skipped += 1
                continue
            
            print(f"[{processed}] Generating thumbnail for: {key}...", end='\r')
            
            try:
                # Download original
                file_bytes = download_object(key)
                
                # Preprocess & Render
                image = ImagePreprocessor.process(file_bytes, key)
                thumb_bytes = ImagePreprocessor.create_thumbnail(image)
                
                if thumb_bytes:
                    upload_object(thumb_key, thumb_bytes, content_type="image/png")
                    generated += 1
                    print(f"\n   ✅ Generated: {thumb_key}")
                else:
                    print(f"\n   ⚠️ Failed to generate bytes for {key}")
                    errors += 1
                    
            except Exception as e:
                print(f"\n   ❌ Error processing {key}: {e}")
                errors += 1

    except Exception as e:
        print(f"\n❌ Critical error: {e}")

    print("\n" + "=" * 60)
    print("🏁 BACKFILL COMPLETE")
    print(f"Scanned Targets: {processed}")
    print(f"Generated: {generated}")
    print(f"Skipped (Already Existed): {skipped}")
    print(f"Errors: {errors}")
    print("=" * 60)

if __name__ == "__main__":
    backfill_thumbnails()
