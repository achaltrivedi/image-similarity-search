"""
Test script to verify webhook ingestion is working correctly.

This script:
1. Uploads a test image to MinIO
2. Waits for webhook to process it
3. Verifies the image appears in PostgreSQL
"""

import os
import time
import requests
from utils.minio_utils import get_s3_client
from utils.minio_config import BUCKET_NAME
from core.database import SessionLocal, ImageEmbedding

def test_webhook_ingestion():
    print("=" * 60)
    print("WEBHOOK INGESTION TEST")
    print("=" * 60)
    
    # Step 1: Check current database count
    db = SessionLocal()
    initial_count = db.query(ImageEmbedding).count()
    print(f"\n1. Initial database count: {initial_count}")
    db.close()
    
    # Step 2: Upload a test image to MinIO
    # Path is relative to project root if run from root, or ../images from tests/
    test_image_path = "images/img1.png" 
    if not os.path.exists(test_image_path):
        test_image_path = "../images/img1.png"
    test_object_key = f"test_webhook_{int(time.time())}.png"
    
    print(f"\n2. Uploading test image to MinIO...")
    print(f"   Object key: {test_object_key}")
    
    s3 = get_s3_client()
    try:
        s3.upload_file(test_image_path, BUCKET_NAME, test_object_key)
        print("   ✅ Upload successful!")
    except Exception as e:
        print(f"   ❌ Upload failed: {e}")
        return False
    
    # Step 3: Wait for webhook to process
    print(f"\n3. Waiting for webhook to process (10 seconds)...")
    time.sleep(10)
    
    # Step 4: Check if image was indexed
    db = SessionLocal()
    final_count = db.query(ImageEmbedding).count()
    
    # Check if the specific image exists
    new_image = db.query(ImageEmbedding).filter_by(object_key=test_object_key).first()
    db.close()
    
    print(f"\n4. Final database count: {final_count}")
    
    # Step 5: Verify results
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    
    if final_count > initial_count:
        print(f"✅ SUCCESS! Database count increased: {initial_count} → {final_count}")
        
        if new_image:
            print(f"✅ Test image found in database!")
            print(f"   - ID: {new_image.id}")
            print(f"   - Object Key: {new_image.object_key}")
            print(f"   - Created At: {new_image.created_at}")
            print(f"   - Embedding Dimensions: {len(new_image.embedding) if new_image.embedding is not None else 'None'}")
            return True
        else:
            print(f"⚠️  Database count increased, but test image not found")
            print(f"   This might mean another image was indexed")
            return True
    else:
        print(f"❌ FAILED! Database count unchanged: {initial_count}")
        print("\nPossible issues:")
        print("  1. Webhook not configured in MinIO")
        print("  2. Application not running (check uvicorn)")
        print("  3. Webhook endpoint has errors (check app logs)")
        print("  4. Network connectivity issues")
        return False

if __name__ == "__main__":
    # Prerequisites check
    print("\nPrerequisites:")
    print("  1. MinIO server running")
    print("  2. FastAPI app running (uvicorn app:app --reload)")
    print("  3. PostgreSQL container running")
    print("  4. Webhook configured in MinIO")
    print("\nPress Enter to start test...")
    input()
    
    success = test_webhook_ingestion()
    
    if success:
        print("\n🎉 Webhook ingestion is working correctly!")
    else:
        print("\n❌ Webhook ingestion test failed. Check logs above.")
