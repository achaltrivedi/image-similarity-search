# Webhook Testing Guide

## Why Test the Webhook?

After migrating to PostgreSQL, the webhook code path changed significantly:
- **Old**: Updates FAISS index file + JSON metadata file
- **New**: Inserts directly into PostgreSQL database

**Critical Reasons to Test:**
1. ✅ Verify the new code path works
2. ✅ Ensure MinIO → App → Database integration is intact
3. ✅ Catch any errors before production use
4. ✅ Validate that new images get indexed automatically

---

## Quick Test (Manual)

### Step 1: Ensure Everything is Running
```bash
# Check Docker container
docker ps | grep vector_db

# Check FastAPI app
# Should see: INFO: Uvicorn running on http://127.0.0.1:8000
```

### Step 2: Upload an Image to MinIO
Use MinIO Console or CLI:
```bash
# Using MinIO client (mc)
mc cp test_image.png myminio/your-bucket/test_webhook.png
```

### Step 3: Check Application Logs
Look for webhook processing messages:
```
Received webhook payload: {...}
Processing new object: test_webhook.png
Successfully indexed test_webhook.png
```

### Step 4: Verify in Database
```bash
docker exec vector_db psql -U admin -d vectordb -c "SELECT object_key, created_at FROM image_embeddings ORDER BY created_at DESC LIMIT 5;"
```

You should see your newly uploaded image!

---

## Automated Test Script

Run the provided test script:
```bash
python test_webhook.py
```

**What it does:**
1. Counts current database entries
2. Uploads a test image to MinIO
3. Waits 10 seconds for webhook processing
4. Checks if database count increased
5. Verifies the specific image was indexed

---

## Expected Behavior

### Successful Webhook Flow:
```
1. Image uploaded to MinIO
   ↓
2. MinIO sends webhook event to http://127.0.0.1:8000/webhook/minio
   ↓
3. FastAPI receives event, extracts object_key
   ↓
4. Downloads image from MinIO
   ↓
5. Preprocesses image (handles PDF/GIF/etc)
   ↓
6. Generates 768-dim embedding using CLIP
   ↓
7. Inserts into PostgreSQL:
   INSERT INTO image_embeddings (object_key, embedding) VALUES (...)
   ↓
8. Returns success response
```

### Application Logs (Success):
```
Received webhook payload: {'Records': [...]}
Processing new object: test_image.png
Successfully indexed test_image.png
INFO: 127.0.0.1:xxxxx - "POST /webhook/minio HTTP/1.1" 200 OK
```

### Database Verification:
```sql
SELECT COUNT(*) FROM image_embeddings;
-- Should increase by 1

SELECT * FROM image_embeddings WHERE object_key = 'test_image.png';
-- Should return the new record
```

---

## Troubleshooting

### Issue: Webhook not triggered
**Check:**
- Is MinIO webhook configured? (`setup_minio_webhook.py`)
- Is the webhook URL correct? (http://127.0.0.1:8000/webhook/minio)
- Is FastAPI running and accessible?

**Test manually:**
```bash
curl -X POST http://127.0.0.1:8000/webhook/minio \
  -H "Content-Type: application/json" \
  -d @mock_event.json
```

### Issue: Webhook triggered but no database insert
**Check application logs for:**
- Download errors (MinIO connection issues)
- Preprocessing errors (invalid image format)
- Embedding errors (CLIP model issues)
- Database errors (connection, constraint violations)

**Common errors:**
```python
# Duplicate key error (image already indexed)
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint

# Connection error (database not accessible)
psycopg2.OperationalError: connection to server failed

# Missing embedding (model not loaded)
AttributeError: 'NoneType' object has no attribute 'embed_images'
```

### Issue: Database count increases but wrong image
**Possible causes:**
- Another upload happened simultaneously
- Webhook processed a different pending event
- Check `object_key` in database to identify what was indexed

---

## What Success Looks Like

After uploading `test_webhook.png`:

**Database Query:**
```sql
SELECT object_key, created_at, 
       pg_column_size(embedding) as embedding_size 
FROM image_embeddings 
WHERE object_key = 'test_webhook.png';
```

**Expected Output:**
```
   object_key    |         created_at         | embedding_size
-----------------+----------------------------+----------------
 test_webhook.png| 2026-02-06 17:45:23.123+00 |           3076
```

**Embedding size calculation:**
- 768 dimensions × 4 bytes (float32) = 3,072 bytes
- Plus PostgreSQL overhead ≈ 3,076 bytes

---

## Best Practices

1. **Test with different file types:**
   - PNG, JPG (should work)
   - PDF (should extract first page)
   - GIF (should extract first frame)

2. **Test error handling:**
   - Upload invalid file (should fail gracefully)
   - Upload duplicate (should skip or update)

3. **Monitor performance:**
   - Check processing time in logs
   - Verify database doesn't slow down with more images

4. **Production checklist:**
   - [ ] Webhook tested and working
   - [ ] Error handling verified
   - [ ] Database constraints working (unique keys)
   - [ ] Logs are informative
   - [ ] Performance is acceptable

---

## Summary

**Yes, you MUST test webhook ingestion because:**
1. It's a completely new code path (PostgreSQL instead of FAISS)
2. It's the primary way new images get indexed
3. Silent failures would mean new images aren't searchable
4. Better to catch issues now than in production

**Run the test, verify it works, and you'll have confidence that your entire system is functioning correctly!** 🚀
