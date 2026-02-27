import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is importable when run from tools/ or repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from utils.minio_utils import list_all_objects
from utils.minio_config import BUCKET_NAME

def list_files():
    print(f"Listing files in bucket '{BUCKET_NAME}':")
    try:
        found_any = False
        for obj in list_all_objects():
            found_any = True
            print(f" - {obj.object_name} (Size: {obj.size})")

        if not found_any:
            print("   (Bucket is empty)")
    except Exception as e:
        print(f"Error listing files: {e}")

if __name__ == "__main__":
    list_files()
