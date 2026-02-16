from __future__ import annotations

import os

QUEUE_NAME = os.getenv("INGEST_QUEUE_NAME", "minio_ingestion")
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
JOB_TIMEOUT_SECONDS = int(os.getenv("INGEST_JOB_TIMEOUT_SECONDS", "900"))


def _get_backend() -> str:
    # "rq" uses Redis + RQ worker. "inline" executes immediately in API process.
    return os.getenv("INGEST_QUEUE_BACKEND", "rq").lower()


def enqueue_minio_record(record: dict) -> dict:
    backend = _get_backend()

    if backend == "inline":
        from core.ingestion_jobs import process_minio_record

        result = process_minio_record(record)
        return {
            "backend": "inline",
            "queued": False,
            "result": result,
        }

    try:
        from redis import Redis
        from rq import Queue
        from rq import Retry
    except Exception as e:
        raise RuntimeError(
            "RQ backend requested but rq/redis dependencies are missing. "
            "Install requirements or set INGEST_QUEUE_BACKEND=inline."
        ) from e

    redis_conn = Redis.from_url(REDIS_URL)
    queue = Queue(QUEUE_NAME, connection=redis_conn, default_timeout=JOB_TIMEOUT_SECONDS)
    
    # Retry up to 3 times with exponential backoff (10s, 30s, 60s)
    # This handles transient MinIO/Network glitches
    job = queue.enqueue(
        "core.ingestion_jobs.process_minio_record", 
        record,
        retry=Retry(max=3, interval=[10, 30, 60])
    )

    return {
        "backend": "rq",
        "queued": True,
        "job_id": job.id,
        "queue": QUEUE_NAME,
    }


def queue_health() -> dict:
    backend = _get_backend()
    if backend == "inline":
        return {"backend": "inline", "status": "ok"}

    try:
        from redis import Redis
        from rq import Queue
    except Exception:
        return {"backend": "rq", "status": "degraded", "error": "rq_or_redis_dependency_missing"}

    try:
        redis_conn = Redis.from_url(REDIS_URL)
        redis_conn.ping()
        queue = Queue(QUEUE_NAME, connection=redis_conn)
        return {
            "backend": "rq",
            "status": "ok",
            "queue": QUEUE_NAME,
            "queued_jobs": queue.count,
        }
    except Exception as e:
        return {"backend": "rq", "status": "degraded", "error": str(e)}
