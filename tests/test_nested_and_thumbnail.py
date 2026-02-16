
import os
import sys
import io
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Force backend to inline for testing
os.environ["INGEST_QUEUE_BACKEND"] = "inline"

from utils.minio_utils import get_s3_client
from utils.minio_config import BUCKET_NAME
from core.ingestion_jobs import process_minio_record

# Mock AI file (same minimal PDF as before)
DUMMY_AI_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>>>endobj\n"
    b"xref\n"
    b"0 4\n"
    b"0000000000 65535 f\n"
    b"0000000010 00000 n\n"
    b"0000000053 00000 n\n"
    b"0000000102 00000 n\n"
    b"trailer<</Size 4/Root 1 0 R>>\n"
    b"startxref\n"
    b"178\n"
    b"%%EOF\n"
)

def create_dummy_image():
    # Create a 100x100 RGB image
    img = Image.new('RGB', (100, 100), color = 'red')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

def test_nested_and_thumbnail():
    s3 = get_s3_client()
    
    print("🧪 Starting Verification...")

    # 1. Test Nested Path
    nested_key = "folder/subfolder/nested_test.png"
    print(f"\n1. Uploading Nested File: {nested_key}")
    s3.put_object(Bucket=BUCKET_NAME, Key=nested_key, Body=create_dummy_image())
    
    # Process straight away
    print("   Processing...")
    try:
        process_minio_record({
            "eventName": "s3:ObjectCreated:Put",
            "s3": {"object": {"key": nested_key}}
        })
        print("   ✅ Ingestion complete.")
    except Exception as e:
        print(f"   ❌ Ingestion Failed: {e}")
        import traceback
        traceback.print_exc()

    # 2. Test Thumbnail Generation
    ai_key = "test_thumb.ai"
    print(f"\n2. Uploading Mock .ai File: {ai_key}")
    s3.put_object(Bucket=BUCKET_NAME, Key=ai_key, Body=DUMMY_AI_BYTES)
    
    print("   Processing...")
    try:
        process_minio_record({
            "eventName": "s3:ObjectCreated:Put",
            "s3": {"object": {"key": ai_key}}
        })
    except Exception as e:
        print(f"   ❌ Ingestion Failed for AI: {e}")
        import traceback
        traceback.print_exc()

    # Verify Thumbnail Exists
    thumb_key = f".thumbnails/{ai_key}.png"
    try:
        s3.head_object(Bucket=BUCKET_NAME, Key=thumb_key)
        print(f"   ✅ Thumbnail FOUND at {thumb_key}")
    except Exception as e:
        print(f"   ❌ Thumbnail NOT found: {e}")

    print("\n🔍 Verification Complete.")

if __name__ == "__main__":
    try:
        test_nested_and_thumbnail()
    except Exception as e:
        print(f"❌ Test Failed: {e}")
