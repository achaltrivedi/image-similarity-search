# app.py

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
import os
import threading
import json
import hashlib
import redis
from dotenv import load_dotenv

# Load env vars from .env file (for local dev)
load_dotenv()

from core.embedding import ImageEmbedder
from utils.minio_utils import get_s3_client
from utils.minio_config import BUCKET_NAME
from core.preprocessor import ImagePreprocessor
from fastapi import Request
from core.database import SessionLocal, ImageEmbedding, init_db
from core.task_queue import enqueue_minio_record, queue_health

# Initialize Redis client for query caching
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# ------------------------
# CONFIG
# ------------------------
EMBEDDING_DIM = 768   # CLIP ViT-B/32
DEFAULT_TOP_K = 5

# ------------------------
# APP
# ------------------------
app = FastAPI(
    title="In-House Image Similarity Search",
    version="1.0.0"
)

# Enable CORS (Cross-Origin Resource Sharing)
# Allows the API to be called from other domains (e.g., a separate Frontend App)
from fastapi.middleware.cors import CORSMiddleware
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5174").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve images directory at /images for the UI (placeholders, errors, local preview)
base_dir = os.path.dirname(os.path.abspath(__file__))
images_dir = os.path.join(base_dir, "images")
if os.path.exists(images_dir):
    app.mount("/images", StaticFiles(directory=images_dir), name="images")

# ------------------------
# GLOBAL STATE
# ------------------------
embedder: ImageEmbedder | None = None

# Thread lock for safe index reloading without stopping the service
reload_lock = threading.RLock()


# ------------------------
# STARTUP
# ------------------------
@app.on_event("startup")
def startup_event():
    global embedder

    print("Starting Image Similarity Service (PostgreSQL + pgvector Backend)")

    # Initialize database
    init_db()

    # Load embedder (used only for query images)
    embedder = ImageEmbedder()

    # Check database connection
    db = SessionLocal()
    try:
        count = db.query(ImageEmbedding).count()
        print(f"Database connected: {count} vectors loaded")
    finally:
        db.close()

    print("Image Similarity Service is READY")


# ------------------------
# HEALTH CHECK
# ------------------------
@app.get("/health")
def health():
    queue_status = queue_health()
    return {
        "status": "ok",
        "backend": "postgresql",
        "queue": queue_status,
    }


# ------------------------
# RELOAD INDEX ENDPOINT
# ------------------------



# ------------------------
# SEARCH ENDPOINT
# ------------------------
@app.post("/search")
async def search_image(
    file: UploadFile = File(None),
    query_id: str = Form(None),
    page: int = Form(1),
    page_size: int = Form(50),
    similarity_threshold: float = Form(0.0)  # Default: show all results (100% to 0%)
):
    """
    Search for similar images with pagination support.
    
    Args:
        file: Image file to search (required on first request)
        query_id: Cached query ID from previous request (for pagination)
        page: Page number (1-indexed)
        page_size: Results per page (default: 50)
        similarity_threshold: Minimum similarity (0.0-1.0, default: 0.0 = all results)
    
    Returns:
        {
            "results": [...],
            "query_id": "abc123",
            "page": 1,
            "page_size": 50,
            "has_more": true,
            "total_results": 154
        }
    """
    global embedder
    
    # Lazy load embedder
    if embedder is None:
        print("Loading embedder lazily...")
        embedder = ImageEmbedder()
    
    # Get or compute query embedding
    if query_id:
        # Retrieve cached embedding from Redis
        cached_data = redis_client.get(f"query:{query_id}")
        if not cached_data:
            return JSONResponse(
                status_code=400,
                content={"error": "Query ID expired or invalid. Please upload image again."}
            )
        query_vector = json.loads(cached_data)
    else:
        # First request: compute embedding and cache it
        if not file:
            return JSONResponse(
                status_code=400,
                content={"error": "Either 'file' or 'query_id' must be provided"}
            )
        
        image_bytes = await file.read()
        
        # Enforce file size limit (50MB)
        MAX_FILE_SIZE = 50 * 1024 * 1024
        if len(image_bytes) > MAX_FILE_SIZE:
            return JSONResponse(
                status_code=413,
                content={"error": f"File too large ({len(image_bytes) // (1024*1024)}MB). Maximum is 50MB."}
            )
        
        # Use Preprocessor to handle PDF/GIF inputs
        try:
            image = ImagePreprocessor.process(image_bytes, file.filename)
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": f"Invalid file: {str(e)}"})
        
        # Generate embedding
        query_embedding = embedder.embed_images([image])
        query_np = query_embedding.cpu().numpy()[0]
        query_vector = query_np.tolist()
        
        # Generate unique query ID and cache embedding (5 min TTL)
        query_id = hashlib.md5(image_bytes).hexdigest()
        redis_client.setex(f"query:{query_id}", 300, json.dumps(query_vector))
    
    # Calculate pagination offset
    offset = (page - 1) * page_size
    
    # Query PostgreSQL with pagination
    db = SessionLocal()
    try:
        # Get total count (for has_more calculation)
        total_query = db.query(ImageEmbedding).filter(
            ImageEmbedding.embedding.cosine_distance(query_vector) <= (1 - similarity_threshold)
        )
        total_results = total_query.count()
        
        # Get paginated results
        results_query = db.query(
            ImageEmbedding.object_key,
            ImageEmbedding.embedding.cosine_distance(query_vector).label('distance')
        ).filter(
            ImageEmbedding.embedding.cosine_distance(query_vector) <= (1 - similarity_threshold)
        ).order_by('distance').limit(page_size).offset(offset)
        
        results = []
        print(f"Search page {page} returned {results_query.count()} results")
        
        # Try to get S3 client — gracefully degrade if MinIO is unavailable
        try:
            s3 = get_s3_client()
            s3_available = True
        except Exception as e:
            print(f"Warning: S3/MinIO unavailable, URLs will be empty: {e}")
            s3 = None
            s3_available = False
        
        for row in results_query:
            key = row.object_key
            similarity = 1 - row.distance
            
            image_url = None
            thumbnail_url = None
            download_url = None
            
            if s3_available and s3:
                try:
                    # 1. URL for original file (view)
                    image_url = s3.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': BUCKET_NAME, 'Key': key},
                        ExpiresIn=3600
                    )
                    
                    # 2. URL for download
                    filename = key.split('/')[-1]
                    download_url = s3.generate_presigned_url(
                        'get_object',
                        Params={
                            'Bucket': BUCKET_NAME, 
                            'Key': key,
                            'ResponseContentDisposition': f'attachment; filename="{filename}"'
                        },
                        ExpiresIn=3600
                    )
                    
                    # 3. URL for thumbnail
                    if key.lower().endswith((".ai", ".pdf")):
                        thumb_key = f".thumbnails/{key}.png"
                        thumbnail_url = s3.generate_presigned_url(
                            'get_object',
                            Params={'Bucket': BUCKET_NAME, 'Key': thumb_key},
                            ExpiresIn=3600
                        )
                    else:
                        thumbnail_url = image_url

                except Exception as e:
                    print(f"Error generating presigned URL for {key}: {e}")

            results.append({
                "image_key": key,
                "similarity": float(similarity),
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "download_url": download_url
            })
    finally:
        db.close()

    return {
        "results": results,
        "query_id": query_id,
        "page": page,
        "page_size": page_size,
        "has_more": (offset + len(results)) < total_results,
        "total_results": total_results
    }


# ------------------------
# WEBHOOK ENDPOINT
# ------------------------
@app.post("/webhook/minio")
async def minio_webhook(request: Request):
    """
    Receives S3/MinIO bucket notification events.
    Enqueues ingestion tasks to background workers.
    """
    try:
        payload = await request.json()
        print(f"Received webhook payload: {payload}")
        
        if "Records" not in payload:
            return JSONResponse(status_code=400, content={"error": "Invalid payload"})

        accepted = 0
        queued = 0
        failed = 0
        job_ids: list[str] = []

        for record in payload["Records"]:
            try:
                enqueue_result = enqueue_minio_record(record)
                accepted += 1
                if enqueue_result.get("queued"):
                    queued += 1
                    job_id = enqueue_result.get("job_id")
                    if job_id:
                        job_ids.append(job_id)
            except Exception as e:
                failed += 1
                print(f"Failed to enqueue webhook record: {e}")

        return {
            "status": "accepted",
            "accepted": accepted,
            "queued": queued,
            "failed": failed,
            "job_ids": job_ids,
        }
        
    except Exception as e:
        print(f"Webhook error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/", response_class=None)
def home():
        """Minimal web UI for quick manual testing."""
        html = """
        <!doctype html>
        <html>
            <head>
                <meta charset="utf-8" />
                <title>Image Similarity</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 24px; }
                    .controls { margin-bottom: 12px; }
                    .result { display:inline-block; width:220px; margin:8px; text-align:center; vertical-align:top }
                    .result img { width:200px; height:auto; border:1px solid #ddd; padding:4px; }
                    .status { color:#666; margin-bottom:8px }
                </style>
            </head>
            <body>
                <h2>Image Similarity</h2>
                <div class="controls">
                    <input id="file" type="file" accept="*/*" />
                    <button id="btn" onclick="upload()">Search</button>
                </div>
                <div id="status" class="status"></div>
                <div id="results"></div>

                <script>
                    async function upload(){
                        const f = document.getElementById('file').files[0];
                        if(!f){ alert('Choose an image first'); return; }
                        const fd = new FormData(); fd.append('file', f);

                        document.getElementById('status').innerText = 'Searching...';
                        const resp = await fetch('/search', { method: 'POST', body: fd });
                        const data = await resp.json();
                        document.getElementById('status').innerText = '';

                        const container = document.getElementById('results'); container.innerHTML = '';
                        if(!data.results || data.results.length === 0){ container.innerText = 'No results'; return; }

                        data.results.forEach(r => {
                            const div = document.createElement('div'); div.className = 'result';
                            const name = (r.image_key || '').split('/').pop() || 'Unknown';
                            
                            // Check content type
                            const isPdf = name.toLowerCase().endsWith('.ai') || name.toLowerCase().endsWith('.pdf');
                            
                            // 1. Thumbnail / Image Display
                            const img = document.createElement('img');
                            // Use the thumbnail_url if available, falling back to image_url
                            img.src = r.thumbnail_url || r.image_url || '/images/placeholder.png';
                            img.onerror = function(){ this.src = '/images/error.png'; };
                            
                            // Wrap in link to original file
                            const link = document.createElement('a');
                            link.href = r.image_url;
                            link.target = "_blank";
                            link.appendChild(img);
                            div.appendChild(link);

                            // 2. Metadata
                            const p = document.createElement('div'); 
                            p.innerText = name + ' — ' + (r.similarity*100).toFixed(2) + '%';
                            div.appendChild(p); 
                            
                            // 3. Download Button
                            if (r.download_url) {
                                const downloadBtn = document.createElement('a');
                                downloadBtn.href = r.download_url;
                                downloadBtn.innerText = '⬇️ Download';
                                downloadBtn.style.cssText = 'display:inline-block; margin-top:8px; padding:6px 12px; background:#007bff; color:#fff; text-decoration:none; border-radius:4px; font-size:12px;';
                                div.appendChild(downloadBtn);
                            }
                            
                            container.appendChild(div);
                        });
                    }
                </script>
            </body>
        </html>
        """

        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html)
