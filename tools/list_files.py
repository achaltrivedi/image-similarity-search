import sys
from pathlib import Path

# Ensure project root is importable when run from tools/ or repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.minio_utils import get_s3_client
from utils.minio_config import BUCKET_NAME

def list_files():
    s3 = get_s3_client()
    print(f"Listing files in bucket '{BUCKET_NAME}':")
    try:
        paginator = s3.get_paginator("list_objects_v2")
        found_any = False
        for page in paginator.paginate(Bucket=BUCKET_NAME):
            for obj in page.get("Contents", []):
                found_any = True
                print(f" - {obj['Key']} (Size: {obj['Size']})")

        if not found_any:
            print("   (Bucket is empty)")
    except Exception as e:
        print(f"Error listing files: {e}")

if __name__ == "__main__":
    list_files()
