"""
End-to-end async ingestion verification script.

Validates:
1) API health reports queue backend/status
2) Upload to MinIO triggers webhook -> queue -> worker -> DB upsert
3) Deleting object triggers webhook -> queue -> worker -> DB delete
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.request import urlopen

# Ensure project root is importable when running as: python tools/test_async_pipeline.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.database import ImageEmbedding, SessionLocal
from utils.minio_config import BUCKET_NAME
from utils.minio_utils import get_s3_client


def fetch_health(api_base_url: str) -> dict:
    url = f"{api_base_url.rstrip('/')}/health"
    with urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_db_record(object_key: str) -> ImageEmbedding | None:
    db = SessionLocal()
    try:
        return db.query(ImageEmbedding).filter_by(object_key=object_key).first()
    finally:
        db.close()


def wait_for(condition_fn, timeout_seconds: int, poll_seconds: float) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if condition_fn():
            return True
        time.sleep(poll_seconds)
    return False


def ensure_test_image() -> str:
    candidates = [
        Path("images/img1.png"),
        Path("../images/img1.png"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    raise FileNotFoundError("Could not find test image. Expected images/img1.png")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify async ingestion pipeline.")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000", help="FastAPI base URL")
    parser.add_argument("--timeout", type=int, default=90, help="Wait timeout in seconds for each phase")
    parser.add_argument("--poll", type=float, default=2.0, help="Polling interval in seconds")
    args = parser.parse_args()

    print("=" * 72)
    print("ASYNC INGESTION PIPELINE TEST")
    print("=" * 72)

    try:
        health = fetch_health(args.api_url)
    except (URLError, HTTPError, TimeoutError) as e:
        print(f"FAIL: Could not reach API health endpoint: {e}")
        return 1
    except Exception as e:
        print(f"FAIL: Unexpected error reading health endpoint: {e}")
        return 1

    queue = health.get("queue", {})
    queue_backend = queue.get("backend")
    queue_status = queue.get("status")
    print(f"Health queue backend={queue_backend} status={queue_status}")

    if queue_backend != "rq":
        print("FAIL: Queue backend is not 'rq'. Set INGEST_QUEUE_BACKEND=rq.")
        return 1
    if queue_status != "ok":
        print(f"FAIL: Queue status is not ok: {queue}")
        return 1

    test_image_path = ensure_test_image()
    object_key = f"e2e_async_{int(time.time())}.png"
    s3 = get_s3_client()

    print(f"Uploading test file: {object_key}")
    try:
        s3.upload_file(test_image_path, BUCKET_NAME, object_key)
    except Exception as e:
        print(f"FAIL: Upload failed: {e}")
        return 1

    print("Waiting for DB upsert from worker...")
    indexed = wait_for(
        lambda: get_db_record(object_key) is not None,
        timeout_seconds=args.timeout,
        poll_seconds=args.poll,
    )
    if not indexed:
        print(f"FAIL: Record not indexed within {args.timeout}s for key={object_key}")
        return 1
    print("PASS: Record indexed.")

    print(f"Deleting test file: {object_key}")
    try:
        s3.delete_object(Bucket=BUCKET_NAME, Key=object_key)
    except Exception as e:
        print(f"FAIL: Delete request failed: {e}")
        return 1

    print("Waiting for synchronized DB delete from worker...")
    deleted = wait_for(
        lambda: get_db_record(object_key) is None,
        timeout_seconds=args.timeout,
        poll_seconds=args.poll,
    )
    if not deleted:
        print(f"FAIL: Record not deleted within {args.timeout}s for key={object_key}")
        return 1
    print("PASS: Record deleted.")

    print("=" * 72)
    print("SUCCESS: Async ingestion pipeline is working end-to-end.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
