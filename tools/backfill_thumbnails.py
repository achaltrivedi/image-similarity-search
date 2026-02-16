import os
import sys
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.preprocessor import ImagePreprocessor
from utils.minio_utils import get_s3_client, SUPPORTED_IMAGE_EXTENSIONS
from utils.minio_config import BUCKET_NAME

def backfill_thumbnails():
    print("=" * 60)
    print("🎨 BACKFILLING MISSING THUMBNAILS")
    print("=" * 60)
    
    s3 = get_s3_client()
    paginator = s3.get_paginator("list_objects_v2")
    
    # Files that need thumbnails
    target_exts = (".ai", ".pdf")
    
    processed = 0
    generated = 0
    skipped = 0
    errors = 0

    try:
        for page in paginator.paginate(Bucket=BUCKET_NAME):
            if "Contents" not in page:
                continue
                
            for obj in page["Contents"]:
                key = obj["Key"]
                
                # Skip thumbnails themselves
                if key.startswith(".thumbnails/"):
                    continue
                    
                # Only check likely targets (AI/PDF)
                if not key.lower().endswith(target_exts):
                    continue

                processed += 1
                thumb_key = f".thumbnails/{key}.png"
                
                # Check if thumbnail exists
                try:
                    s3.head_object(Bucket=BUCKET_NAME, Key=thumb_key)
                    # print(f"   [SKIP] Thumbnail exists for {key}")
                    skipped += 1
                    continue
                except:
                    # Thumbnail missing, generate it
                    pass
                
                print(f"[{processed}] Generating thumbnail for: {key}...", end='\r')
                
                try:
                    # Download original
                    response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
                    file_bytes = response['Body'].read()
                    
                    # Preprocess & Render
                    image = ImagePreprocessor.process(file_bytes, key)
                    thumb_bytes = ImagePreprocessor.create_thumbnail(image)
                    
                    if thumb_bytes:
                        s3.put_object(
                            Bucket=BUCKET_NAME,
                            Key=thumb_key,
                            Body=thumb_bytes,
                            ContentType="image/png"
                        )
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
