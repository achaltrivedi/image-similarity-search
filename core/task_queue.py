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


def enqueue_full_sync() -> dict:
    """Enqueues a full bucket sync if one is not already running."""
    backend = _get_backend()

    if backend == "inline":
        from tools.batch_indexer import batch_index_images
        batch_index_images(force_reindex=False)
        return {
            "backend": "inline",
            "queued": False,
            "status": "completed",
        }

    try:
        from redis import Redis
        from rq import Queue
    except Exception as e:
        raise RuntimeError(
            "RQ backend requested but rq/redis dependencies are missing."
        ) from e

    redis_conn = Redis.from_url(REDIS_URL)
    queue = Queue(QUEUE_NAME, connection=redis_conn, default_timeout=86400) # 24h timeout for full sync

    # Use Redis as a lock to prevent multiple concurrent syncs
    LOCK_KEY = "manual_sync_in_progress"
    
    # Check if lock exists (is currently syncing)
    if redis_conn.exists(LOCK_KEY):
        return {
            "backend": "rq",
            "queued": False,
            "status": "already_running",
            "message": "A bucket sync is already in progress."
        }
        
    # Set the lock (expires unconditionally after 6 hours to prevent deadlocks if worker crashes)
    redis_conn.setex(LOCK_KEY, 21600, "1")

    # Enqueue a wrapper function that runs the indexer AND releases the lock when done
    job = queue.enqueue(
        "core.task_queue._run_locked_sync", 
        job_timeout="24h"
    )

    return {
        "backend": "rq",
        "queued": True,
        "job_id": job.id,
        "queue": QUEUE_NAME,
        "status": "started",
        "message": "Bucket sync started in the background."
    }

def _run_locked_sync():
    """Wrapper function that runs batch indexer and then releases the Redis lock."""
    from tools.batch_indexer import batch_index_images
    from redis import Redis
    
    redis_conn = Redis.from_url(REDIS_URL)
    LOCK_KEY = "manual_sync_in_progress"
    
    try:
        batch_index_images(force_reindex=False)
    finally:
        # Always release the lock when finished or failed
        redis_conn.delete(LOCK_KEY)


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
