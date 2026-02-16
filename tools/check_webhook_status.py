"""
Diagnostic script to check webhook configuration status.
"""

import sys
from pathlib import Path

import requests

# Ensure project root is importable when run from tools/ or repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.minio_utils import get_s3_client
from utils.minio_config import BUCKET_NAME, MINIO_ENDPOINT


def check_webhook_status():
    print("=" * 60)
    print("WEBHOOK DIAGNOSTIC CHECK")
    print("=" * 60)

    # 1. Check if FastAPI is running
    print("\n1. Checking FastAPI application...")
    try:
        response = requests.get("http://127.0.0.1:8000/docs", timeout=10)
        if response.status_code == 200:
            print("   [OK] FastAPI is running on http://127.0.0.1:8000")
        else:
            print(f"   [WARN] FastAPI responded with status {response.status_code}")
    except Exception as e:
        print(f"   [FAIL] FastAPI is NOT running: {e}")
        print("   -> Start it with: uvicorn app:app --reload")
        return

    # 2. Check webhook endpoint
    print("\n2. Checking webhook endpoint...")
    try:
        test_payload = {
            "Records": [
                {
                    "eventName": "s3:ObjectCreated:Put",
                    "s3": {
                        "object": {
                            "key": "diagnostic_test.png"
                        }
                    }
                }
            ]
        }
        response = requests.post(
            "http://127.0.0.1:8000/webhook/minio",
            json=test_payload,
            timeout=10,
        )
        print("   [OK] Webhook endpoint is accessible")
        print(f"   Response status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   [FAIL] Webhook endpoint error: {e}")

    # 3. Check MinIO connection
    print("\n3. Checking MinIO connection...")
    try:
        s3 = get_s3_client()
        buckets = s3.list_buckets()
        print(f"   [OK] MinIO is accessible at {MINIO_ENDPOINT}")
        print(f"   Buckets: {[b['Name'] for b in buckets['Buckets']]}")
    except Exception as e:
        print(f"   [FAIL] MinIO connection failed: {e}")
        return

    # 4. Check bucket notification configuration
    print("\n4. Checking bucket notification configuration...")
    try:
        s3 = get_s3_client()
        config = s3.get_bucket_notification_configuration(Bucket=BUCKET_NAME)

        if "QueueConfigurations" in config and len(config["QueueConfigurations"]) > 0:
            print("   [OK] Webhook is configured")
            for queue_config in config["QueueConfigurations"]:
                print(f"      - ID: {queue_config.get('Id')}")
                print(f"      - ARN: {queue_config.get('QueueArn')}")
                print(f"      - Events: {queue_config.get('Events')}")
        else:
            print(f"   [FAIL] NO webhook configured for bucket '{BUCKET_NAME}'")
            print(f"\n   Current configuration: {config}")
    except Exception as e:
        print(f"   [WARN] Could not retrieve notification config: {e}")

    # 5. Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("\nTo configure MinIO webhook, you need to:")
    print("1. Restart MinIO with webhook environment variables")
    print("2. Run: python tools/setup_minio_webhook.py")


if __name__ == "__main__":
    check_webhook_status()
