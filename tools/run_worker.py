import os
import sys
from pathlib import Path

from redis import Redis
from rq import Queue, SimpleWorker, Worker

# Ensure project root is importable when run from tools/ or repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    queue_name = os.getenv("INGEST_QUEUE_NAME", "minio_ingestion")

    redis_conn = Redis.from_url(redis_url)
    queue = Queue(queue_name, connection=redis_conn)

    worker_cls = SimpleWorker if os.name == "nt" else Worker
    print(
        f"Starting RQ worker ({worker_cls.__name__}) "
        f"for queue='{queue_name}' redis='{redis_url}'"
    )
    worker = worker_cls([queue], connection=redis_conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
