# MinIO Integration Changes for app.py

## Summary
Updated `app.py` and `faiss_index.py` to use MinIO as the source of truth for images instead of local storage. The application now:
- Loads images from MinIO S3 bucket during startup
- Builds and persists FAISS index locally for fast restarts
- Returns presigned URLs to MinIO images in search results

## Changes Made

### 1. **app.py - Imports**
**Added:**
```python
import json
from minio_utils import load_images_from_minio, get_s3_client
from minio_config import BUCKET_NAME
```
**Reason:** Import MinIO utilities and bucket configuration

### 2. **app.py - Global State**
**Changed:**
- Removed: `image_names` → Now using `image_keys` (MinIO object keys)
- Removed: `/images` static file mount (not needed anymore)
- Added: `INDEX_PERSIST_PATH` and `METADATA_PERSIST_PATH` for local caching

```python
image_keys = []  # MinIO object keys in same order as FAISS index
INDEX_PERSIST_PATH = "faiss_index.bin"
METADATA_PERSIST_PATH = "index_metadata.json"
```

### 3. **app.py - Startup Event**
**Complete Redesign:**
The startup now follows this flow:

```
Check if local index exists?
    ├─ YES: Load from disk (fast restart ~1 second)
    └─ NO: Load from MinIO → Generate embeddings → Build index → Save to disk
```

**Key Features:**
- First startup: Fetches images from MinIO, generates embeddings, builds index
- Subsequent startups: Uses cached index files for instant startup
- Stores image_keys in `index_metadata.json` to maintain mapping

### 4. **app.py - Search Endpoint**
**Changed:**
The `/search` endpoint now:
- ✅ Still accepts uploaded image
- ✅ Generates embedding
- ✅ Searches FAISS index
- ✨ **NEW**: Returns presigned URLs from MinIO instead of local file paths
- ✨ **NEW**: Uses MinIO object keys (`image_key`) instead of file names

**Response Format:**
```json
{
  "results": [
    {
      "image_key": "folder/image1.jpg",
      "similarity": 98.5,
      "image_url": "http://minio:9000/bucket/folder/image1.jpg?X-Amz-Algorithm=..."
    }
  ]
}
```

### 5. **faiss_index.py - Persistence**
**Added two new methods:**

```python
def save(self, path: str):
    """Persist index to disk"""
    faiss.write_index(self.index, path)

def load(self, path: str):
    """Load index from disk"""
    self.index = faiss.read_index(path)
```
**Reason:** Allow index caching to avoid rebuilding on every restart

---

## Workflow Diagram

### First Startup (MinIO)
```
app.startup()
  ├─ Load ImageEmbedder
  ├─ Check for cached files → NOT FOUND
  ├─ Load images from MinIO
  ├─ Generate embeddings
  ├─ Build FAISS index
  ├─ Save faiss_index.bin + index_metadata.json
  └─ Ready for search
```

### Subsequent Startups (Cached)
```
app.startup()
  ├─ Load ImageEmbedder
  ├─ Check for cached files → FOUND
  ├─ Load faiss_index.bin
  ├─ Load image_keys from index_metadata.json
  └─ Ready for search (2-3 seconds vs 2-5 minutes)
```

### Search Request
```
POST /search
  ├─ User uploads query image
  ├─ Generate embedding
  ├─ Search FAISS index
  ├─ Get MinIO object keys from results
  ├─ Generate presigned URLs for each result
  └─ Return results with URLs
```

---

## Environment Dependencies

Make sure your `minio_config.py` has:
```python
MINIO_ENDPOINT = "http://minio:9000"
MINIO_ACCESS_KEY = "your-access-key"
MINIO_SECRET_KEY = "your-secret-key"
BUCKET_NAME = "your-bucket-name"
```

---

## Benefits

| Before | After |
|--------|-------|
| Images stored in `/images` directory | Images in MinIO bucket (source of truth) |
| Local filesystem dependency | Cloud-based, scalable storage |
| Slow startup (embed all images) | Fast startup (use cached index) |
| Limited access control | S3 presigned URLs with expiry |
| N/A | Easily scalable to millions of images |

---

## Testing the Changes

### 1. **First Run (Build Index)**
```bash
python -m uvicorn app:app --reload
```
Should output:
```
🚀 Starting Image Similarity Service (MinIO Backend)
🔹 Building new index from MinIO...
✅ Found X images in MinIO bucket
🔹 Generating embeddings...
🔹 Building FAISS index...
💾 Persisting index to disk...
✅ Service ready with X images indexed
```

### 2. **Subsequent Runs (Use Cache)**
```bash
python -m uvicorn app:app --reload
```
Should output:
```
🚀 Starting Image Similarity Service (MinIO Backend)
📦 Loading existing FAISS index from disk...
✅ Loaded index with X images
```

### 3. **Test Search**
```bash
curl -X POST "http://localhost:8000/search" \
  -F "file=@test_image.jpg" \
  -F "top_k=5"
```

Should return:
```json
{
  "results": [
    {
      "image_key": "images/similar1.jpg",
      "similarity": 95.2,
      "image_url": "http://minio:9000/bucket/images/similar1.jpg?X-Amz-..."
    }
  ]
}
```

---

## Files Modified

- [app.py](app.py) - Complete redesign for MinIO integration
- [faiss_index.py](faiss_index.py) - Added save/load methods

## Files Referenced (No Changes Needed)

- `embedding.py` - ✓ Works as-is
- `faiss_index.py` - ✓ Enhanced
- `minio_utils.py` - ✓ Used by app.py
- `minio_config.py` - ✓ Configuration source
- `main.py` - ⚠️ Can be deprecated (local loading no longer needed)
