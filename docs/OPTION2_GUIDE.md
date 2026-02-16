# Step-by-Step Guide: Adding MinIO to Docker Compose

## What We're Doing

Adding MinIO to your `docker-compose.yml` so that:
1. MinIO runs in a Docker container (consistent environment)
2. MinIO knows about your FastAPI webhook endpoint
3. Everything starts with one command: `docker-compose up -d`

---

## Steps to Follow

### Step 1: Stop Current Services
```bash
# Stop any running MinIO instance
docker stop minio 2>$null  # If MinIO was running in Docker
# OR kill MinIO process if running directly on Windows

# Stop current docker-compose services
docker-compose down
```

### Step 2: Start All Services
```bash
# Start both PostgreSQL and MinIO
docker-compose up -d

# Verify both are running
docker-compose ps
```

**Expected output:**
```
NAME        IMAGE                    STATUS
minio       minio/minio             Up
vector_db   pgvector/pgvector:pg16  Up
```

### Step 3: Create Bucket (First Time Only)
```bash
# Access MinIO Console
# Open browser: http://localhost:9090
# Login: minioadmin / minioadmin
# Create bucket named: image-similarity-test
```

**OR use Python:**
```python
from minio_utils import get_s3_client
s3 = get_s3_client()
s3.create_bucket(Bucket='image-similarity-test')
```

### Step 4: Configure Bucket Notification
```bash
python setup_minio_webhook.py
```

**Expected output:**
```
Bucket notification synced!
```

### Step 5: Verify Configuration
```bash
python check_webhook_status.py
```

**Expected output:**
```
✅ FastAPI is running on http://127.0.0.1:8000
✅ Webhook endpoint is accessible
✅ MinIO is accessible at http://localhost:9000
✅ Webhook is configured!
   - ID: FastAPI-Webhook
   - ARN: arn:minio:sqs::primary:webhook
   - Events: ['s3:ObjectCreated:*']
```

### Step 6: Test End-to-End
```bash
python test_webhook.py
```

**Expected output:**
```
✅ SUCCESS! Database count increased: 18 → 19
✅ Test image found in database!
```

---

## Understanding the Configuration

### Key Environment Variables

```yaml
MINIO_NOTIFY_WEBHOOK_ENABLE_primary: "on"
```
- Enables a webhook target named "primary"
- This creates the ARN: `arn:minio:sqs::primary:webhook`

```yaml
MINIO_NOTIFY_WEBHOOK_ENDPOINT_primary: "http://host.docker.internal:8000/webhook/minio"
```
- URL where MinIO will send events
- `host.docker.internal` = special DNS name that resolves to host machine from inside Docker
- Port 8000 = your FastAPI app

### Network Flow

```
MinIO Container (port 9000)
    ↓
host.docker.internal:8000
    ↓
Your FastAPI App (running on host)
    ↓
PostgreSQL Container (port 5433→5432)
```

---

## Troubleshooting

### Issue: "Bucket notification synced!" but webhook still not working

**Check:**
```bash
# 1. Is FastAPI running?
curl http://127.0.0.1:8000/docs

# 2. Can MinIO reach FastAPI?
docker exec minio curl http://host.docker.internal:8000/webhook/minio
```

### Issue: "Connection refused" when accessing MinIO

**Solution:**
```bash
# Check if MinIO is running
docker logs minio

# Restart if needed
docker-compose restart minio
```

### Issue: Bucket notification fails with "ARN does not exist"

**Solution:**
```bash
# Restart MinIO to reload environment variables
docker-compose restart minio

# Wait 5 seconds, then try again
python setup_minio_webhook.py
```

---

## What Happens Next

Once configured, **every image you upload to MinIO will automatically:**
1. Trigger a webhook event
2. Get downloaded by FastAPI
3. Generate an embedding using CLIP
4. Insert into PostgreSQL
5. Become searchable immediately!

**No manual indexing needed!** 🎉

---

## Quick Reference

```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# View logs
docker-compose logs -f minio
docker-compose logs -f db

# Restart a service
docker-compose restart minio

# Access MinIO Console
# http://localhost:9090
# Login: minioadmin / minioadmin

# Access FastAPI Docs
# http://localhost:8000/docs
```

---

## Next Steps After Setup

1. ✅ Upload test images via MinIO Console
2. ✅ Watch app logs to see webhook processing
3. ✅ Query database to verify indexing
4. ✅ Test search functionality in UI

**You're all set!** 🚀
