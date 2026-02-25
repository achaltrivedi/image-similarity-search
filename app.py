# app.py

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
import os
import io
import base64
import threading
import json
import hashlib
import redis
from PIL import Image
from dotenv import load_dotenv

# Load env vars from .env file (for local dev)
load_dotenv()

from core.embedding import ImageEmbedder
from core.similarity_analyzer import explain_similarity
from core.design_features import extract_design_features
from utils.minio_utils import get_s3_client, get_public_s3_client, get_bucket_keys
from utils.minio_config import BUCKET_NAME
from core.preprocessor import ImagePreprocessor
from fastapi import Request
from core.database import SessionLocal, ImageEmbedding, init_db
from core.task_queue import enqueue_minio_record, queue_health

# Lazy Redis client (avoids crash if Redis starts after the app)
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client

# Concurrency limiter: max 3 simultaneous CLIP inferences to prevent OOM
_embed_semaphore = threading.Semaphore(3)

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
    
    # Check Redis connectivity
    redis_status = "ok"
    try:
        get_redis().ping()
    except Exception as e:
        redis_status = f"degraded: {e}"
    
    return {
        "status": "ok",
        "backend": "postgresql",
        "queue": queue_status,
        "redis": redis_status,
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
    
    # Initialize variables used in both first-request and paginated paths
    query_design_vector = None
    query_image_for_explain = None
    
    # Lazy load embedder
    if embedder is None:
        print("Loading embedder lazily...")
        embedder = ImageEmbedder()
    
    # Get or compute query embedding
    if query_id:
        # Retrieve cached embedding from Redis
        try:
            cached_data = get_redis().get(f"query:{query_id}")
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content={"error": f"Cache service unavailable: {e}. Please try again."}
            )
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
        
        # Generate embedding (with concurrency limit to prevent GPU OOM)
        with _embed_semaphore:
            query_embedding = embedder.embed_images([image])
        query_np = query_embedding.cpu().numpy()[0]
        query_vector = query_np.tolist()
        
        # Generate design feature vector for structural search
        try:
            query_design_vector = extract_design_features(image)
        except Exception:
            query_design_vector = None
        
        # Generate unique query ID and cache embedding + design + image (5 min TTL)
        query_id = hashlib.md5(image_bytes).hexdigest()
        query_image_for_explain = image  # Keep PIL image for similarity explainer
        try:
            r = get_redis()
            r.setex(f"query:{query_id}", 300, json.dumps(query_vector))
            if query_design_vector:
                r.setex(f"query_design:{query_id}", 300, json.dumps(query_design_vector))
            # Cache the image too (for similarity explainer on paginated requests)
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            r.setex(f"query_img:{query_id}", 300, base64.b64encode(buf.getvalue()).decode())
        except Exception as e:
            print(f"Warning: Failed to cache query in Redis: {e}")
            # Search still works without caching, just can't paginate
    
    # Get cached set of keys that actually exist in the bucket
    try:
        bucket_keys = get_bucket_keys()
    except Exception as e:
        print(f"Warning: Could not fetch bucket keys, skipping existence filter: {e}")
        bucket_keys = None  # Skip filtering if bucket is unreachable
    
    # Recover design query vector (for paginated requests)
    if query_design_vector is None:
        try:
            cached_dv = get_redis().get(f"query_design:{query_id}")
            if cached_dv:
                query_design_vector = json.loads(cached_dv)
        except Exception:
            pass
    
    # Query PostgreSQL — fetch ALL matching results with both distances
    db = SessionLocal()
    try:
        # Build query with CLIP distance + optional design distance
        clip_distance = ImageEmbedding.embedding.cosine_distance(query_vector).label('clip_distance')
        
        if query_design_vector:
            design_distance = ImageEmbedding.design_embedding.cosine_distance(query_design_vector).label('design_distance')
            results_query = db.query(
                ImageEmbedding.object_key,
                clip_distance,
                design_distance,
                ImageEmbedding.minio_metadata
            ).filter(
                ImageEmbedding.embedding.cosine_distance(query_vector) <= (1 - similarity_threshold)
            ).order_by('clip_distance')  # Initial ordering by CLIP, re-sorted below
        else:
            results_query = db.query(
                ImageEmbedding.object_key,
                clip_distance,
                ImageEmbedding.minio_metadata
            ).filter(
                ImageEmbedding.embedding.cosine_distance(query_vector) <= (1 - similarity_threshold)
            ).order_by('clip_distance')
        
        # Filter results — rank by CLIP similarity (overall)
        all_matches = []
        for row in results_query:
            if bucket_keys is not None and row.object_key not in bucket_keys:
                continue  # Skip — image no longer in bucket
            
            clip_sim = float(1 - row.clip_distance)
            
            # Design similarity for display (not ranking)
            design_sim = None
            if query_design_vector and hasattr(row, 'design_distance') and row.design_distance is not None:
                design_sim = float(1 - row.design_distance)
            
            # Extract file size
            file_size = None
            if hasattr(row, 'minio_metadata') and row.minio_metadata:
                file_size = row.minio_metadata.get("file_size")
            
            all_matches.append((row.object_key, clip_sim, design_sim, file_size))
        
        # Sort by CLIP similarity (overall) — pure semantic ranking
        all_matches.sort(key=lambda x: x[1], reverse=True)
        
        # Paginate the filtered results in Python
        total_results = len(all_matches)
        offset = (page - 1) * page_size
        page_matches = all_matches[offset:offset + page_size]
        
        print(f"Search page {page}: {len(page_matches)} results (filtered {total_results} from DB)")
        
        # Use public S3 client for presigned URLs (browser-accessible endpoint)
        try:
            s3 = get_public_s3_client()
            s3_available = True
        except Exception as e:
            print(f"Warning: S3/MinIO unavailable, URLs will be empty: {e}")
            s3 = None
            s3_available = False
        
        # Recover query image for similarity explainer
        # (available directly on first request, loaded from Redis cache on pagination)
        if query_image_for_explain is None:
            try:
                cached_img = get_redis().get(f"query_img:{query_id}")
                if cached_img:
                    img_bytes = base64.b64decode(cached_img)
                    query_image_for_explain = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            except Exception:
                pass  # Scores will be empty if image not available
        
        # Use internal S3 client for downloading result images (for explainer)
        try:
            s3_internal = get_s3_client()
        except Exception:
            s3_internal = None
        
        results = []
        for key, similarity, design_sim, file_size in page_matches:
            image_url = None
            thumbnail_url = None
            download_url = None
            similarity_scores = {"design": design_sim}  # From DB (design_embedding)
            
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
            
            # Get color + texture scores from image analysis
            if query_image_for_explain and s3_internal:
                try:
                    obj = s3_internal.get_object(Bucket=BUCKET_NAME, Key=key)
                    result_bytes = obj["Body"].read()
                    result_pil = ImagePreprocessor.process(result_bytes, key)
                    color_score, texture_score = explain_similarity(query_image_for_explain, result_pil)
                    similarity_scores["color"] = color_score
                    similarity_scores["texture"] = texture_score
                except Exception:
                    pass  # Scores remain None if analysis fails

            results.append({
                "image_key": key,
                "similarity": similarity,
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "download_url": download_url,
                "similarity_scores": similarity_scores,
                "file_size": file_size
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
