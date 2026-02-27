# Image Similarity Microservice

A production-ready image similarity search microservice that ingests, indexes, and retrieves visually similar graphical assets at scale. Built to handle 300k+ images stored in S3-compatible object storage (MinIO), with real-time event-driven ingestion.

**Supports:** PNG, JPEG, PDF, AI (Adobe Illustrator), GIF, TIFF, BMP, WebP

---

## Table of Contents

- [Quick Start](#quick-start-local-development)
- [Architecture](#architecture)
- [Embedding Pipeline](#embedding-pipeline)
- [Real-Time Ingestion](#real-time-ingestion)
- [Docker Compose](#docker-compose-full-stack)
- [Key Files](#key-files)
- [Useful Commands](#useful-commands)

---

## Quick Start (Local Development)

### Prerequisites

- **Docker Desktop** (running)
- **Python 3.10+**
- **Node.js 18+** and npm
- A `.env` file (see below)

### 1. Clone & Setup

```bash
git clone https://github.com/achaltrivedi/image-similarity-microservice.git
cd image-similarity-microservice

# Create and activate Python virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure `.env`

Create a `.env` file in the project root:

```env
# Database
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_password
POSTGRES_DB=vectordb
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5434

# MinIO (Object Storage)
MINIO_ROOT_USER=your_minio_access_key
MINIO_ROOT_PASSWORD=your_minio_secret_key
MINIO_BUCKET_NAME=your_bucket_name
MINIO_ENDPOINT=http://your-minio-host:9000
MINIO_PUBLIC_ENDPOINT=http://your-minio-host:9000

# Redis
REDIS_URL=redis://127.0.0.1:6379/0

# Application
WEBHOOK_SECRET=your_webhook_secret
INGEST_QUEUE_BACKEND=rq
INGEST_QUEUE_NAME=minio_ingestion

# Hugging Face
HF_TOKEN=your_hf_token
```

### 3. Start Infrastructure

```bash
docker-compose up -d db redis

# Verify containers are running
docker ps
```

### 4. Initialize Database

```bash
# With venv activated:
python tools/init_db.py
```

This creates the `pgvector` extension, `image_embeddings` table with all 4 vector columns, and HNSW indexes.

### 5. Start Backend

```bash
# Terminal 1 — API Server
uvicorn app:app --reload

# Terminal 2 — Background Worker + Event Listener
python tools/run_worker.py
```

Wait for `Image Similarity Service is READY` in the API terminal.
The worker terminal should show `🔗 [listener] MinIO event listener started`.

### 6. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at: **<http://localhost:5173>**

### 7. Index Existing Images

```bash
# Verify bucket connection
python tools/debug_bucket_contents.py

# Index all images from the bucket into pgvector
python tools/batch_indexer.py
```

### 8. Test It

Open **<http://localhost:5173>**, upload an image, and search.

---

## Architecture

```text
                         ┌─────────────────────────────────────────┐
                         │        run_worker.py (single process)   │
MinIO (S3)               │                                         │
   │                     │  Thread 1: RQ Worker                    │
   │  listen_bucket_     │  ─────────────────                      │
   ├──notification()────▶│  Picks jobs from Redis, processes them  │
   │  (minio-py SDK)     │  (embed, thumbnail, store in Postgres)  │
   │                     │                                         │
   │                     │  Thread 2: MinIO Event Listener          │
   │                     │  ───────────────────────────────         │
   │                     │  Streams upload/delete events            │
   │                     │  Enqueues into Redis via task_queue.py   │
                         └─────────────────────────────────────────┘
                                          │
               ┌──────────────────────────┼──────────────────────┐
               ▼                          ▼                      ▼
         CLIP Embed (768d)     Design/Color/Texture       Thumbnail → MinIO
               │               Embeddings (256/64d)              │
               └──────────┬───────────────┘                      │
                          ▼                                      │
                    PostgreSQL (pgvector)                         │
                          │                                      │
               ┌──────────┴───────────┐                          │
               ▼                      ▼                          ▼
          Search API ──────────▶ React Frontend ◀───── Presigned URLs
         (FastAPI)                (Vite + React)
```

### Services

| Service         | Port | Description                           |
| --------------- | ---- | ------------------------------------- |
| FastAPI Backend | 8000 | Search API + webhook + sync endpoints |
| React Frontend  | 5173 | Upload & search UI (dev)              |
| React Frontend  | 80   | Upload & search UI (Docker/Nginx)     |
| PostgreSQL      | 5434 | Vector database (pgvector + HNSW)     |
| Redis           | 6379 | Background job queue (RQ)             |
| MinIO API       | 9000 | S3-compatible object storage          |
| MinIO Console   | 9001 | MinIO web UI                          |

---

## Embedding Pipeline

Each image is represented by **4 vector embeddings**, all computed at ingestion time:

| Embedding        | Dimensions | Model / Method              | Purpose            |
| ---------------- | ---------- | --------------------------- | ------------------ |
| `embedding`      | 768        | CLIP ViT-B/32               | Semantic similarity|
| `design_embedding` | 256      | Edge density grid (Canny)   | Structural layout  |
| `color_embedding`  | 256      | HSV histogram (mean-centered) | Color palette    |
| `texture_embedding` | 64     | Grayscale histogram (mean-centered) | Surface texture |

All vectors are L2-normalized and mean-centered (where applicable) so that PostgreSQL's native `cosine_distance()` equals the Pearson Correlation Coefficient.

Each embedding column has a dedicated **HNSW index** for sub-millisecond similarity search.

---

## Real-Time Ingestion

The worker process (`tools/run_worker.py`) runs two threads:

1. **RQ Worker** — processes queued ingestion jobs (download → preprocess → embed → store)
2. **MinIO Event Listener** — uses `minio-py` SDK's `listen_bucket_notification()` to stream `s3:ObjectCreated` and `s3:ObjectRemoved` events in real-time

When you upload/delete an image via MinIO Console or the S3 API, the listener immediately enqueues a job. The worker picks it up and processes it within seconds.

**Fallback:** The "Sync Bucket" button in the frontend manually diffs MinIO vs PostgreSQL and indexes any missing images.

---

## Docker Compose (Full Stack)

All services build from a single root `Dockerfile` using multi-stage build targets (CPU-only PyTorch for minimal image size).

```bash
docker-compose up -d
```

This starts: PostgreSQL, Redis, MinIO, Backend API, Workers (×4), Frontend (Nginx on port 80).

| Build Target | Used By         | Description               |
| ------------ | --------------- | ------------------------- |
| `api`        | `app`, `worker` | Python FastAPI + Worker   |
| `frontend`   | `frontend`      | React app served by Nginx |

---

## Key Files

| File                             | Purpose                                          |
| -------------------------------- | ------------------------------------------------ |
| `app.py`                         | FastAPI — search, health, webhook, sync endpoints |
| `Dockerfile`                     | Multi-stage build (API + Frontend, CPU-only)      |
| `docker-compose.yml`             | Full stack orchestration with health checks       |
| `nginx.conf`                     | Nginx config for SPA + API proxy                  |
| `core/embedding.py`              | CLIP model for semantic image embeddings          |
| `core/color_texture_features.py` | HSV color + grayscale texture feature extractors  |
| `core/design_features.py`        | Edge density grid for structural embeddings       |
| `core/preprocessor.py`           | Image format conversion (PDF, AI → RGB)           |
| `core/database.py`               | SQLAlchemy models + pgvector (4 vector columns)   |
| `core/minio_listener.py`         | Real-time MinIO event listener (minio-py SDK)     |
| `core/task_queue.py`             | Redis Queue job management + sync locking         |
| `core/ingestion_jobs.py`         | Full ingestion pipeline (download → embed → store)|
| `utils/minio_utils.py`           | S3 client helpers + bucket key cache              |
| `utils/minio_config.py`          | Environment-driven MinIO config                   |
| `tools/run_worker.py`            | RQ worker + event listener launcher               |
| `tools/batch_indexer.py`         | Bulk index existing images (4 vectors per image)  |
| `tools/init_db.py`               | Database schema setup (tables, columns, indexes)  |
| `tools/cleanup_stale_entries.py` | Remove orphaned DB entries                        |
| `frontend/`                      | React + Vite search UI (dark mode, shadcn/ui)     |

---

## Useful Commands

```bash
# Check system health
curl http://localhost:8000/health

# List bucket contents
python tools/debug_bucket_contents.py

# Batch index all images (generates all 4 embeddings per image)
python tools/batch_indexer.py

# Clean up stale DB entries (images deleted from bucket)
python tools/cleanup_stale_entries.py --dry-run   # preview
python tools/cleanup_stale_entries.py              # execute

# Backfill missing thumbnails for AI/PDF files
python tools/backfill_thumbnails.py

# Check webhook status
python tools/check_webhook_status.py
```
