# Async Ingestion Guide (Redis + RQ)

This project now supports queue-based webhook ingestion:

- FastAPI webhook endpoint only accepts and enqueues records.
- Worker process consumes jobs and performs embedding + DB upsert/delete.

## 1. Start infrastructure

```powershell
docker compose up -d redis db minio
```

## 2. Install dependencies

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 3. Start API

```powershell
.\venv\Scripts\uvicorn.exe app:app --reload
```

## 4. Start worker (separate terminal)

```powershell
.\venv\Scripts\python.exe tools/run_worker.py
```

## 5. Verify health

```powershell
curl http://127.0.0.1:8000/health
```

Expected queue status fields:

- `queue.backend`: `rq`
- `queue.status`: `ok`

## Environment variables

- `INGEST_QUEUE_BACKEND`: `rq` (default) or `inline`
- `REDIS_URL`: default `redis://127.0.0.1:6379/0`
- `INGEST_QUEUE_NAME`: default `minio_ingestion`
- `INGEST_JOB_TIMEOUT_SECONDS`: default `900`

Use `INGEST_QUEUE_BACKEND=inline` only for local debugging without Redis.
