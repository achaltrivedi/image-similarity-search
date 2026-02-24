# Image Similarity Search Microservice

## Overview
A production-ready image similarity search microservice that ingests, indexes, and retrieves visually similar graphical assets at scale. Built to handle 300k+ images stored in S3-compatible object storage (MinIO), with real-time webhook-driven ingestion.

**Supports:** PNG, JPEG, PDF, AI (Adobe Illustrator), GIF, TIFF, BMP, WebP

---

## Quick Start (Local Development)

### Prerequisites
- **Docker Desktop** (running)
- **Python 3.10+**
- **Node.js 18+** and npm
- A `.env` file (see below)

### 1. Clone & Setup

```bash
# Clone the repo
git clone https://github.com/achaltrivedi/image-similarity-microservice.git
cd image-similarity-microservice

# Create Python virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure `.env`

Create a `.env` file in the project root (copy from `.env.example` if available):

```env
# --- Database ---
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_password
POSTGRES_DB=vectordb
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5434

# --- MinIO (Object Storage) ---
MINIO_ROOT_USER=your_minio_access_key
MINIO_ROOT_PASSWORD=your_minio_secret_key
MINIO_BUCKET_NAME=your_bucket_name
MINIO_ENDPOINT=http://your-minio-host:9000
MINIO_PUBLIC_ENDPOINT=http://your-minio-host:9000

# --- Redis ---
REDIS_URL=redis://127.0.0.1:6379/0

# --- Application ---
WEBHOOK_SECRET=your_webhook_secret
INGEST_QUEUE_BACKEND=rq
INGEST_QUEUE_NAME=minio_ingestion

# --- Hugging Face ---
HF_TOKEN=your_hf_token
```

### 3. Start Infrastructure (Docker)

```bash
# Start PostgreSQL (pgvector) + Redis
docker-compose up -d db redis

# Verify containers are running
docker ps
```

### 4. Start Backend

```bash
# With venv activated:
uvicorn app:app --reload
```

Wait for: `Image Similarity Service is READY`

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at: **http://localhost:5173**

### 6. Index Existing Images

```bash
# Verify bucket connection
python tools/debug_bucket_contents.py

# Index all images from the bucket into pgvector
python tools/batch_indexer.py
```

### 7. Test It

Open **http://localhost:5173**, upload an image, and search!

---

## Architecture

```
MinIO (S3) ──webhook──▶ FastAPI ──▶ Redis Queue ──▶ Workers
                           │                          │
                           ▼                          ▼
                     Search API            Embed + Store in
                           │              PostgreSQL (pgvector)
                           ▼
                    React Frontend
```

| Service | Port | Description |
|---|---|---|
| FastAPI Backend | 8000 | Search API + webhook endpoint |
| React Frontend | 5173 | Upload & search UI |
| PostgreSQL | 5434 | Vector database (pgvector) |
| Redis | 6379 | Background job queue |
| MinIO | 9000 | S3-compatible object storage |

---

## Useful Commands

```bash
# Check system health
curl http://localhost:8000/health

# List bucket contents
python tools/debug_bucket_contents.py

# Batch index all images
python tools/batch_indexer.py

# Clean up stale DB entries (images deleted from bucket)
python tools/cleanup_stale_entries.py --dry-run   # preview
python tools/cleanup_stale_entries.py              # execute

# Backfill missing thumbnails for AI/PDF files
python tools/backfill_thumbnails.py

# Check webhook status
python tools/check_webhook_status.py
```

---

## Docker Compose (Full Stack)

To run everything in Docker (no local Python/Node needed):

```bash
docker-compose up -d
```

This starts: PostgreSQL, Redis, Backend API, Workers (×4), Frontend (Nginx)

---

## Key Files

| File | Purpose |
|---|---|
| `app.py` | FastAPI application — search, health, webhook endpoints |
| `core/embedding.py` | CLIP model for generating image embeddings |
| `core/preprocessor.py` | Image format conversion (PDF, AI → RGB) |
| `core/database.py` | SQLAlchemy models + pgvector integration |
| `core/task_queue.py` | Redis Queue job management |
| `utils/minio_utils.py` | S3 client helpers + bucket key cache |
| `utils/minio_config.py` | Environment-driven MinIO config |
| `tools/batch_indexer.py` | Bulk index existing images |
| `tools/cleanup_stale_entries.py` | Remove orphaned DB entries |
| `frontend/` | React + Vite search UI |

---


