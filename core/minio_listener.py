"""
Real-time MinIO event listener using the minio-py SDK.

Streams bucket events (upload/delete) and enqueues them into
the existing RQ pipeline for processing by the worker.
"""

from __future__ import annotations

import os
import time
import threading
from urllib.parse import urlparse

from minio import Minio

from utils.minio_config import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    BUCKET_NAME,
)

RECONNECT_DELAY = 5  # seconds between reconnection attempts


def _build_minio_client() -> Minio:
    """Create a minio-py client from existing env vars."""
    parsed = urlparse(MINIO_ENDPOINT)
    host = parsed.hostname or "localhost"
    port = parsed.port
    secure = parsed.scheme == "https"

    endpoint = f"{host}:{port}" if port else host

    return Minio(
        endpoint,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=secure,
    )


def _listener_loop():
    """Blocking loop that listens for MinIO events and enqueues them."""
    from core.task_queue import enqueue_minio_record

    while True:
        try:
            client = _build_minio_client()
            print(f"🔗 [listener] MinIO event listener started for bucket '{BUCKET_NAME}'")
            print(f"   Endpoint: {MINIO_ENDPOINT} | Access Key: {MINIO_ACCESS_KEY[:6]}...")

            events = client.listen_bucket_notification(
                BUCKET_NAME,
                events=["s3:ObjectCreated:*", "s3:ObjectRemoved:*"],
            )

            for event in events:
                records = event.get("Records") or []
                for record in records:
                    event_name = record.get("eventName", "")
                    object_key = record.get("s3", {}).get("object", {}).get("key", "?")
                    print(f"📥 [listener] Event: {event_name} → {object_key}")

                    try:
                        enqueue_minio_record(record)
                    except Exception as e:
                        print(f"⚠️ [listener] Failed to enqueue {object_key}: {e}")

        except Exception as e:
            print(f"⚠️ [listener] Connection lost ({e}), reconnecting in {RECONNECT_DELAY}s...")
            time.sleep(RECONNECT_DELAY)


def start_minio_listener():
    """Spawn the event listener in a daemon thread (non-blocking)."""
    thread = threading.Thread(target=_listener_loop, daemon=True, name="minio-listener")
    thread.start()
    return thread
