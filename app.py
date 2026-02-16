# app.py

from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
import os
import threading
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
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
    file: UploadFile = File(...),
    top_k: int = DEFAULT_TOP_K
):
    global embedder

    # Lazy load
    if embedder is None:
        print("Loading embedder lazily...")
        embedder = ImageEmbedder()

    image_bytes = await file.read()
    
    # Use Preprocessor to handle PDF/GIF inputs for search queries too
    try:
        image = ImagePreprocessor.process(image_bytes, file.filename)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Invalid file: {str(e)}"})

    # Generate embedding for query image
    query_embedding = embedder.embed_images([image])
    query_np = query_embedding.cpu().numpy()[0]  # Get first (and only) embedding

    # Query PostgreSQL using pgvector cosine similarity
    db = SessionLocal()
    try:
        # Convert numpy array to list for PostgreSQL
        query_vector = query_np.tolist()
        
        # Use pgvector's cosine distance operator (<=>)
        # Lower distance = more similar
        results_query = db.query(
            ImageEmbedding.object_key,
            ImageEmbedding.embedding.cosine_distance(query_vector).label('distance')
        ).order_by('distance').limit(top_k)
        
        results = []
        s3 = get_s3_client()
        print(f"Search returned {top_k} candidates")
        
        for row in results_query:
            key = row.object_key
            # Convert distance to similarity score (1 - distance)
            similarity = 1 - row.distance
            
            image_url = None
            thumbnail_url = None
            try:
                # 1. URL for original file (download/view)
                image_url = s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': BUCKET_NAME, 'Key': key},
                    ExpiresIn=3600
                )
                
                # 2. URL for thumbnail (display)
                if key.lower().endswith((".ai", ".pdf")):
                    thumb_key = f".thumbnails/{key}.png"
                    thumbnail_url = s3.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': BUCKET_NAME, 'Key': thumb_key},
                        ExpiresIn=3600
                    )
                else:
                    # Standard images use themselves as thumbnails
                    thumbnail_url = image_url

            except Exception as e:
                print(f"Error generating presigned URL for {key}: {e}")

            results.append({
                "image_key": key,
                "similarity": float(similarity),
                "image_url": image_url,
                "thumbnail_url": thumbnail_url
            })
    finally:
        db.close()

    return {"results": results}


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
                            container.appendChild(div);
                        });
                    }
                </script>
            </body>
        </html>
        """

        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html)
