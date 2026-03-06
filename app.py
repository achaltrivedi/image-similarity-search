# app.py

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, Query
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
import asyncio

# Load env vars from .env file (for local dev)
load_dotenv()

from core.embedding import ImageEmbedder
from core.color_texture_features import extract_color_features, extract_texture_features
from core.design_features import extract_design_features
from utils.minio_utils import get_bucket_keys, presigned_url, presigned_download_url
from utils.minio_config import BUCKET_NAME
from core.preprocessor import ImagePreprocessor
from fastapi import Request
from core.task_queue import enqueue_minio_record, queue_health, enqueue_full_sync
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

# ------------------------
# WEBSOCKET MANAGER
# ------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

ws_manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup."""
    asyncio.create_task(redis_listener_loop())

async def redis_listener_loop():
    """Background loop that listens to Redis Pub/Sub for newly indexed images."""
    r = get_redis()
    pubsub = r.pubsub()
    pubsub.subscribe("gallery_updates")
    
    # Run in executor to not block the main async loop with synchronous Redis calls
    loop = asyncio.get_running_loop()
    def get_message():
        # Use a short timeout so it doesn't block indefinitely
        return pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
        
    while True:
        try:
            message = await loop.run_in_executor(None, get_message)
            if message and message["type"] == "message":
                data = json.loads(message["data"])
                # Broadcast the newly indexed item to all connected WebSockets
                await ws_manager.broadcast(data)
        except Exception as e:
            print(f"Redis PubSub listener error: {e}")
            await asyncio.sleep(5) # Back off on error
        await asyncio.sleep(0.1) # Small sleep to prevent high CPU

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
        query_np = query_embedding[0]
        query_vector = query_np.tolist()
        
        # Generate design feature vector for structural search
        try:
            query_design_vector = extract_design_features(image)
            query_color = extract_color_features(image)
            query_texture = extract_texture_features(image)
        except Exception:
            query_design_vector = None
            query_color = None
            query_texture = None
        
        # Generate unique query ID and cache embeddings (5 min TTL)
        query_id = hashlib.md5(image_bytes).hexdigest()
        try:
            r = get_redis()
            r.setex(f"query:{query_id}", 300, json.dumps(query_vector))
            if query_design_vector:
                r.setex(f"query_design:{query_id}", 300, json.dumps(query_design_vector))
            if query_color:
                r.setex(f"query_color:{query_id}", 300, json.dumps(query_color))
            if query_texture:
                r.setex(f"query_texture:{query_id}", 300, json.dumps(query_texture))
        except Exception as e:
            print(f"Warning: Failed to cache query in Redis: {e}")
            # Search still works without caching, just can't paginate
    
    # Get cached set of keys that actually exist in the bucket
    try:
        bucket_keys = get_bucket_keys()
    except Exception as e:
        print(f"Warning: Could not fetch bucket keys, skipping existence filter: {e}")
        bucket_keys = None  # Skip filtering if bucket is unreachable
    
    # Recover query vectors (for paginated requests)
    if query_design_vector is None:
        try:
            r = get_redis()
            cached_dv = r.get(f"query_design:{query_id}")
            if cached_dv:
                query_design_vector = json.loads(cached_dv)
                
            cached_c = r.get(f"query_color:{query_id}")
            if cached_c:
                query_color = json.loads(cached_c)
                
            cached_t = r.get(f"query_texture:{query_id}")
            if cached_t:
                query_texture = json.loads(cached_t)
        except Exception:
            query_color = None
            query_texture = None
    
    # Query PostgreSQL — fetch ALL matching results with both distances
    db = SessionLocal()
    try:
        # Build query with CLIP distance + optional design distance
        clip_distance = ImageEmbedding.embedding.cosine_distance(query_vector).label('clip_distance')
        
        # Build optional distance projections
        projections = [
            ImageEmbedding.object_key,
            clip_distance,
            ImageEmbedding.minio_metadata
        ]
        
        if query_design_vector:
            projections.append(ImageEmbedding.design_embedding.cosine_distance(query_design_vector).label('design_distance'))
            
        if query_color:
            projections.append(ImageEmbedding.color_embedding.cosine_distance(query_color).label('color_distance'))
            
        if query_texture:
            projections.append(ImageEmbedding.texture_embedding.cosine_distance(query_texture).label('texture_distance'))

        results_query = db.query(*projections).filter(
            ImageEmbedding.embedding.cosine_distance(query_vector) <= (1 - similarity_threshold)
        ).order_by('clip_distance')
        
        # Filter results — rank by CLIP similarity (overall)
        all_matches = []
        
        for row in results_query:
            if bucket_keys is not None and row.object_key not in bucket_keys:
                continue  # Skip — image no longer in bucket
            
            clip_sim = float(1 - row.clip_distance)
            
            # Extract similarities natively from DB
            design_sim = 0.0
            if query_design_vector and hasattr(row, 'design_distance') and row.design_distance is not None:
                design_sim = float(1 - row.design_distance)
                
            color_sim = 0.0
            if query_color and hasattr(row, 'color_distance') and row.color_distance is not None:
                color_sim = max(0.0, float(1 - row.color_distance))
                
            texture_sim = 0.0
            if query_texture and hasattr(row, 'texture_distance') and row.texture_distance is not None:
                texture_sim = max(0.0, float(1 - row.texture_distance))
            
            # Extract file size
            file_size = None
            if hasattr(row, 'minio_metadata') and row.minio_metadata:
                file_size = row.minio_metadata.get("file_size")
            
            all_matches.append((row.object_key, clip_sim, design_sim, color_sim, texture_sim, file_size))
        
        # Sort by CLIP similarity (overall) — pure semantic ranking
        all_matches.sort(key=lambda x: x[1], reverse=True)
        
        # Paginate the filtered results in Python
        total_results = len(all_matches)
        offset = (page - 1) * page_size
        page_matches = all_matches[offset:offset + page_size]
        
        print(f"Search page {page}: {len(page_matches)} results (filtered {total_results} from DB)")
        
        results = []
        for key, similarity, design_sim, color_sim, texture_sim, file_size in page_matches:
            image_url = None
            thumbnail_url = None
            download_url = None
            similarity_scores = {
                "design": design_sim,
                "color": round(color_sim, 3),
                "texture": round(texture_sim, 3)
            }
            
            try:
                # 1. URL for original file (view)
                image_url = presigned_url(key)
                
                # 2. URL for download (always the original file)
                filename = key.split('/')[-1]
                download_url = presigned_download_url(key, filename)
                
                # 3. URL for thumbnail (always use lightweight .thumbnails/ version)
                thumb_key = f".thumbnails/{key}.png"
                try:
                    thumbnail_url = presigned_url(thumb_key)
                    
                    # For AI/PDF files, use thumbnail as the "view" URL
                    # since browsers can't render .ai files and may auto-download them
                    if key.lower().endswith(('.ai', '.pdf')):
                        image_url = thumbnail_url
                except Exception:
                    thumbnail_url = image_url  # Fallback to full image

            except Exception as e:
                print(f"Error generating presigned URL for {key}: {e}")

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


@app.websocket("/ws/gallery")
async def websocket_gallery(websocket: WebSocket):
    """WebSocket endpoint for real-time gallery updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, though we only push from the server side
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


# ------------------------
# GALLERY / DATA ENDPOINT
# ------------------------

def _format_file_size(size_bytes):
    """Convert bytes to human-readable string."""
    if not size_bytes or size_bytes == 0:
        return "Unknown"
    k = 1024
    sizes = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(size_bytes)
    while size >= k and i < len(sizes) - 1:
        size /= k
        i += 1
    return f"{size:.1f} {sizes[i]}"


def _get_pending_keys() -> list[str]:
    """Get object keys currently queued or being processed in RQ.
    
    Inspects both queued jobs and the currently executing job (started registry)
    to build a list of keys that are 'in flight'.
    """
    try:
        from rq import Queue
        from rq.job import Job
        
        r = get_redis()
        queue = Queue(QUEUE_NAME, connection=r)
        
        pending = []
        
        # 1. Jobs waiting in queue
        for job in queue.jobs:
            try:
                record = job.args[0] if job.args else {}
                key = record.get("s3", {}).get("object", {}).get("key")
                if key:
                    from urllib.parse import unquote_plus
                    pending.append(unquote_plus(key))
            except Exception:
                pass
        
        # 2. Jobs currently being executed (started registry)
        started = queue.started_job_registry
        for job_id in started.get_job_ids():
            try:
                job = Job.fetch(job_id, connection=r)
                record = job.args[0] if job.args else {}
                key = record.get("s3", {}).get("object", {}).get("key")
                if key:
                    from urllib.parse import unquote_plus
                    pending.append(unquote_plus(key))
            except Exception:
                pass
        
        return pending
    except Exception as e:
        print(f"Warning: Could not fetch pending keys: {e}")
        return []


QUEUE_NAME = os.getenv("INGEST_QUEUE_NAME", "minio_ingestion")

@app.get("/gallery")
def get_gallery(page: int = 1, page_size: int = 50, q: str = Query(None)):
    """
    Returns a paginated list of all items currently in the database.
    Also returns a list of actively processing items from Redis.
    Supports optional text search via 'q' parameter.
    """
    if page < 1:
        page = 1
    if page_size > 100:
        page_size = 100
        
    offset = (page - 1) * page_size
    
    db = SessionLocal()
    try:
        # Build base query
        base_query = db.query(ImageEmbedding)
        
        # Apply search filter if provided
        if q:
            base_query = base_query.filter(ImageEmbedding.object_key.ilike(f"%{q}%"))
            
        # Count total rows matching filter
        total = base_query.count()
        
        # Fetch only metadata columns (never return huge vector arrays)
        rows = (
            db.query(
                ImageEmbedding.id,
                ImageEmbedding.object_key,
                ImageEmbedding.created_at,
                ImageEmbedding.minio_metadata,
            )
            .filter(ImageEmbedding.object_key.ilike(f"%{q}%") if q else True)
            .order_by(ImageEmbedding.id.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        
        items = []
        for row in rows:
            key = row.object_key
            filename = key.split("/")[-1] if "/" in key else key
            ext = filename.rsplit(".", 1)[-1].upper() if "." in filename else "—"
            
            # Extract file size from minio_metadata JSON
            metadata = row.minio_metadata or {}
            size_bytes = metadata.get("file_size", 0)
            
            # Generate URLs
            thumb_url = None
            img_url = None
            dl_url = None
            try:
                thumb_key = f".thumbnails/{key}.png"
                thumb_url = presigned_url(thumb_key)
                
                # For AI/PDF, view URL = thumbnail; otherwise = original
                if key.lower().endswith(('.ai', '.pdf')):
                    img_url = thumb_url
                else:
                    img_url = presigned_url(key)
                
                dl_url = presigned_download_url(key, filename)
            except Exception:
                pass
            
            items.append({
                "id": row.id,
                "object_key": key,
                "filename": filename,
                "type": ext,
                "size": _format_file_size(size_bytes),
                "size_bytes": size_bytes,
                "status": "Done",
                "indexed_date": row.created_at.strftime("%Y-%m-%d %H:%M") if row.created_at else "—",
                "thumbnail_url": thumb_url,
                "image_url": img_url,
                "download_url": dl_url,
            })
        
        # Get pending items (in queue but not yet in DB)
        pending_keys = _get_pending_keys()
        indexed_keys = {item["object_key"] for item in items}
        
        pending_items = []
        for pkey in pending_keys:
            if pkey not in indexed_keys:
                pfilename = pkey.split("/")[-1] if "/" in pkey else pkey
                pext = pfilename.rsplit(".", 1)[-1].upper() if "." in pfilename else "—"
                pending_items.append({
                    "id": None,
                    "object_key": pkey,
                    "filename": pfilename,
                    "type": pext,
                    "size": "—",
                    "size_bytes": 0,
                    "status": "Processing",
                    "indexed_date": "—",
                    "thumbnail_url": None,
                    "image_url": None,
                    "download_url": None,
                })
        
        return {
            "items": items,
            "pending": pending_items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_more": (offset + len(items)) < total,
        }
    except Exception as e:
        print(f"Gallery endpoint error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()


from pydantic import BaseModel

class DeleteRequest(BaseModel):
    object_keys: list[str]

@app.delete("/gallery")
def delete_gallery_items(req: DeleteRequest):
    """
    Deletes objects from MinIO by key. The existing event listener
    pipeline will handle DB cleanup and WebSocket notifications.
    """
    if not req.object_keys:
        return {"deleted": 0, "failed": 0, "errors": []}
    
    from utils.minio_utils import get_minio_client
    client = get_minio_client()
    
    deleted = 0
    failed = 0
    errors = []
    
    for key in req.object_keys:
        try:
            client.remove_object(BUCKET_NAME, key)
            # Also remove the thumbnail if it exists
            try:
                client.remove_object(BUCKET_NAME, f".thumbnails/{key}.png")
            except Exception:
                pass  # Thumbnail may not exist
            deleted += 1
        except Exception as e:
            failed += 1
            errors.append({"object_key": key, "error": str(e)})
    
    return {"deleted": deleted, "failed": failed, "errors": errors}


@app.post("/sync_bucket")
async def sync_bucket():
    """
    Manually triggers a background job to scan the MinIO bucket and index missing images.
    Uses a Redis lock to ensure only one sync can run at a time.
    """
    try:
        result = enqueue_full_sync()
        status_code = 202 if result.get("status") == "started" else 200
        return JSONResponse(status_code=status_code, content=result)
    except Exception as e:
        print(f"Error starting sync: {e}")
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
