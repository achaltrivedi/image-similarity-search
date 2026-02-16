# MinIO Webhook Setup Guide

## Problem Identified

Your test showed: **MinIO webhook is NOT configured**

**What happened:**
1. ✅ Image uploaded to MinIO successfully
2. ❌ MinIO did NOT send webhook event to FastAPI
3. ❌ FastAPI never received the event
4. ❌ Image was NOT indexed in PostgreSQL

**Root cause:** MinIO doesn't know about your FastAPI webhook endpoint.

---

## Solution: Configure MinIO Webhook

### Option 1: Restart MinIO with Webhook Config (Recommended)

#### Step 1: Stop Current MinIO
```bash
# Find MinIO container/process and stop it
docker stop minio  # if running in Docker
# OR kill the MinIO process if running directly
```

#### Step 2: Start MinIO with Webhook Environment Variables

**If using Docker:**
```bash
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9090:9090 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  -e "MINIO_NOTIFY_WEBHOOK_ENABLE_primary=on" \
  -e "MINIO_NOTIFY_WEBHOOK_ENDPOINT_primary=http://host.docker.internal:8000/webhook/minio" \
  -v minio_data:/data \
  minio/minio server /data --console-address ":9090"
```

**If running MinIO directly (Windows):**
```powershell
# Set environment variables
$env:MINIO_ROOT_USER="minioadmin"
$env:MINIO_ROOT_PASSWORD="minioadmin"
$env:MINIO_NOTIFY_WEBHOOK_ENABLE_primary="on"
$env:MINIO_NOTIFY_WEBHOOK_ENDPOINT_primary="http://127.0.0.1:8000/webhook/minio"

# Start MinIO
minio.exe server C:\minio-data --console-address ":9090"
```

#### Step 3: Configure Bucket Notification
```bash
python setup_minio_webhook.py
```

This will link your bucket to the webhook endpoint.

---

### Option 2: Add to docker-compose.yml (Best for Development)

Add MinIO to your existing `docker-compose.yml`:

```yaml
version: '3.8'

services:
  db:
    # ... existing db config ...

  minio:
    image: minio/minio
    container_name: minio
    ports:
      - "9000:9000"
      - "9090:9090"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
      MINIO_NOTIFY_WEBHOOK_ENABLE_primary: "on"
      MINIO_NOTIFY_WEBHOOK_ENDPOINT_primary: "http://host.docker.internal:8000/webhook/minio"
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9090"
    restart: always

volumes:
  postgres_data:
  minio_data:  # Add this
```

Then:
```bash
docker-compose down
docker-compose up -d
python setup_minio_webhook.py
```

---

## Verification Steps

### 1. Check MinIO Webhook Config
```bash
python check_webhook_status.py
```

Should show:
```
✅ Webhook is configured!
   - ID: FastAPI-Webhook
   - ARN: arn:minio:sqs::primary:webhook
   - Events: ['s3:ObjectCreated:*']
```

### 2. Test Upload
```bash
python test_webhook.py
```

Should show:
```
✅ SUCCESS! Database count increased: 18 → 19
✅ Test image found in database!
```

### 3. Check Application Logs
When you upload an image, you should see:
```
Received webhook payload: {'Records': [...]}
Processing new object: test_image.png
Successfully indexed test_image.png
```

---

## Troubleshooting

### Issue: "Connection refused" when setting up webhook
**Cause:** FastAPI app is not running

**Solution:**
```bash
uvicorn app:app --reload
```

### Issue: Webhook configured but events not received
**Cause:** Network connectivity issue

**Solutions:**
1. If MinIO in Docker, use `http://host.docker.internal:8000/webhook/minio`
2. If MinIO on host, use `http://127.0.0.1:8000/webhook/minio`
3. Check firewall settings

### Issue: "InvalidArgument: A specified destination ARN does not exist"
**Cause:** MinIO doesn't have the webhook target configured

**Solution:** Restart MinIO with the `MINIO_NOTIFY_WEBHOOK_*` environment variables

---

## Understanding the Flow

### Without Webhook (Current State):
```
Upload to MinIO → (nothing happens) → Image NOT indexed
```

### With Webhook (After Configuration):
```
Upload to MinIO
    ↓
MinIO sends HTTP POST to http://127.0.0.1:8000/webhook/minio
    ↓
FastAPI receives event
    ↓
Downloads image from MinIO
    ↓
Generates embedding
    ↓
Inserts into PostgreSQL
    ↓
Image is now searchable! ✅
```

---

## Quick Test After Setup

```bash
# 1. Upload an image via MinIO console or CLI
# Visit: http://localhost:9090 (MinIO Console)

# 2. Check database immediately
docker exec vector_db psql -U admin -d vectordb -c "SELECT COUNT(*) FROM image_embeddings;"

# 3. Check app logs
# Should see: "Successfully indexed <your_image>"
```

---

## Important Notes

1. **Network Connectivity**: MinIO must be able to reach your FastAPI app
   - Same machine: Use `127.0.0.1` or `localhost`
   - MinIO in Docker: Use `host.docker.internal`
   - Different machines: Use actual IP address

2. **Webhook ARN**: The `primary` in the ARN must match the environment variable name:
   - `MINIO_NOTIFY_WEBHOOK_ENABLE_primary` → `arn:minio:sqs::primary:webhook`

3. **Events**: We're listening to `s3:ObjectCreated:*` which includes:
   - `s3:ObjectCreated:Put`
   - `s3:ObjectCreated:Post`
   - `s3:ObjectCreated:Copy`

---

## Next Steps

1. ✅ Configure MinIO webhook (choose Option 1 or 2)
2. ✅ Run `python setup_minio_webhook.py`
3. ✅ Run `python check_webhook_status.py` to verify
4. ✅ Run `python test_webhook.py` to test end-to-end
5. ✅ Upload images and watch them get indexed automatically!

**Once configured, every image you upload to MinIO will be automatically indexed and searchable!** 🚀
