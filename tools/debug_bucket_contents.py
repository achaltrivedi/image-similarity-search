
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env")

from utils.minio_utils import get_s3_client
from utils.minio_config import BUCKET_NAME

def list_all_files():
    print(f"🔍 Listing ALL objects in bucket: '{BUCKET_NAME}'")
    s3 = get_s3_client()
    
    try:
        paginator = s3.get_paginator("list_objects_v2")
        count = 0
        for page in paginator.paginate(Bucket=BUCKET_NAME):
            if "Contents" in page:
                for obj in page["Contents"]:
                    count += 1
                    print(f" - {obj['Key']} (Size: {obj['Size']})")
        
        print(f"\n✅ Total objects found: {count}")
        
    except Exception as e:
        print(f"❌ Error listing bucket: {e}")

if __name__ == "__main__":
    list_all_files()
