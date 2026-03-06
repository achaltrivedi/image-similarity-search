# Image Similarity Search: 20-Week Development Progress Report

This document outlines the chronological development of the Image Similarity Search architecture, breaking down the 27 key software engineering aspects into a structured 15-20 week timeline. It details the systematic approach and solutions implemented at each stage.

---

## Phase 1: Core Foundation & Initial Ingestion (Weeks 1-4)
*Focus: Establishing the indexing pipeline, handling varied file formats, and robust local execution.*

**1. Efficient Working on Different Formats (Improving [preprocessor.py](file:///c:/Users/ACHAL.TRIVEDI/Downloads/InHouse-Indexed%20Search/core/preprocessor.py))**
*   **Solution:** Built a robust [ImagePreprocessor](file:///c:/Users/ACHAL.TRIVEDI/Downloads/InHouse-Indexed%20Search/core/preprocessor.py#5-101) class that handles format negotiation in memory using `Pillow`. Implemented handlers to strip alpha channels, normalize formats (RGBA to RGB), and manage transparency by compositing onto white backgrounds before feeding them to the CLIP model.

**2. Parsing Sub-Directory Structures for Final Formats (.jpeg/.png/.ai/.pdf)**
*   **Solution:** Configured the ingestion scripts to recursively walk MinIO bucket object trees (`client.list_objects(recursive=True)`), explicitly filtering and extracting valid extensions (PNG, JPEG, PDF, AI, WEBP) regardless of nested folder depth.

**3. Hardware Consideration Before Initial Batch Indexing**
*   **Solution:** Optimized PyTorch to use the CPU-only build (`--extra-index-url https://download.pytorch.org/whl/cpu`) inside Docker. Implemented batched processing ([embed_images](file:///c:/Users/ACHAL.TRIVEDI/Downloads/InHouse-Indexed%20Search/core/embedding.py#19-35) processing max 64 items) and a Python threading Semaphore to prevent out-of-memory (OOM) crashes during massive indexing runs. 

**4. Docker Desktop for Storage Tracking & Initial Ingestion Logging**
*   **Solution:** containerized the application using `docker-compose`, spinning up dedicated services for API, Redis, Worker, and PostgreSQL (`pgvector`). Added comprehensive CLI logging during batch indexing to track speeds (imgs/sec), success rates, and errors directly in Docker's stdout.

**5. Displaying Size and Path in S3/MinIO Bucket**
*   **Solution:** Extracted MinIO metadata during indexing and stored it as a `JSONB` payload in the PostgreSQL `image_embeddings` table. Mapped this data to the frontend UI to display formatted file sizes and exact bucket paths.

---

## Phase 2: Advanced Vector Engineering & Multi-Modal Search (Weeks 5-8)
*Focus: Improving search accuracy by analyzing beyond standard CLIP semantics.*

**6. Design, Color, and Texture Embeddings Integration**
*   **Solution:** Expanded the database schema to include specialized vectors: `design_embedding` (256D Edge Density Grid), `color_embedding` (256D HSV Histogram), and `texture_embedding` (64D Grayscale Histogram). Updated the ingestion pipeline to compute and upsert these alongside the standard 768D CLIP semantic vector.

**7. Graphic Content's Parameter-Wise Priority Separation**
*   **Solution:** Updated the PostgreSQL query in [app.py](file:///c:/Users/ACHAL.TRIVEDI/Downloads/InHouse-Indexed%20Search/app.py) to calculate discrete cosine distances for semantics, color, texture, and design. Allowed the frontend to surface these individual scores visually as progress bars to explain *why* an image matched.

**8. HF (Hugging Face) Read-Only Token Integration**
*   **Solution:** Secured model downloading during container startup by supplying a read-only `HF_TOKEN` in the [.env](file:///c:/Users/ACHAL.TRIVEDI/Downloads/InHouse-Indexed%20Search/.env) file, ensuring reliable, authenticated access to the `openai/clip-vit-base-patch32` weights without hitting rate limits.

---

## Phase 3: Scalability, Concurrency, and Data Integrity (Weeks 9-12)
*Focus: Making the system safe for massive asynchronous workloads and preventing stale data.*

**9. Scaling Workers for Simultaneous Uploads**
*   **Solution:** Integrated `Redis` and `RQ` (Redis Queue). Transitioned from inline, blocking execution to asynchronous background workers. This allows the system to easily scale by simply spinning up more worker containers to handle heavy MinIO webhook/event traffic simultaneously.

**10. File Corruption Checks During Batch Ingestion**
*   **Solution:** Wrapped image opening and processing in strict `try/except` blocks. If an image is corrupt (e.g., truncated bytes or invalid magic numbers), the preprocessor logs a specific `UnidentifiedImageError`, skips the file, and gracefully continues the batch without crashing the worker.

**11. Synchronized Deletion (Handling S3 Deletions Gracefully)**
*   **Solution:** Ensure deleted MinIO images disappear from search. *Option 1:* A cron job/endpoint that diffs DB keys vs MinIO keys and deletes orphaned DB rows. *Option 2:* Event listeners listening for `s3:ObjectRemoved:*` events and deleting the corresponding DB row in real-time.

**12. Bucket Cache vs. PGDB Key Mapping (Removing Stale Entries)**
*   **Solution:** Implemented the [get_bucket_keys()](file:///c:/Users/ACHAL.TRIVEDI/Downloads/InHouse-Indexed%20Search/utils/minio_utils.py#91-108) memory cache with a 30-second TTL. Every search explicitly checks `if row.object_key not in bucket_keys: continue`, immediately hiding deleted images from the UI without requiring an expensive, locking DB `DELETE` operation during business hours.

---

## Phase 4: API, Security, & Infrastructure Optimization (Weeks 13-16)
*Focus: Securing the app for organizational use, refining dependencies, and modernizing SDKs.*

**13. API Authentication (In-House Access) & CORS**
*   **Solution:** Configured FastAPI `CORSMiddleware` to strictly allow specific production frontend origins. For API authentication, the architecture was designed to accommodate bearer tokens or IP-based whitelisting to guarantee only internal company traffic can hit the endpoints.

**14. MinIO API Keys and Credential Management**
*   **Solution:** Extracted hardcoded credentials and implemented `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` in the [.env](file:///c:/Users/ACHAL.TRIVEDI/Downloads/InHouse-Indexed%20Search/.env) file for secure, standard authentication. Assessed and handled legacy credential issues seamlessly.

**15. Replacing AWS Boto3 with MinIO-py SDK**
*   **Solution:** Migrated 100% of AWS `boto3` code to `minio-py`. Wrote unified helper functions ([download_object](file:///c:/Users/ACHAL.TRIVEDI/Downloads/InHouse-Indexed%20Search/utils/minio_utils.py#194-202), [presigned_url](file:///c:/Users/ACHAL.TRIVEDI/Downloads/InHouse-Indexed%20Search/utils/minio_utils.py#226-241)). 
*   **Impact:** Removed the massive `botocore` dependency globally.
*   **Reducing Size of Docker Build:** Combined with the CPU-torch optimization and dropping `boto3`, the Docker build footprint dropped significantly, resulting in faster CI/CD pipelines and deployment.

---

## Phase 5: Event-Driven Sync & Modern User Experience (Weeks 17-20)
*Focus: Real-time UI responsiveness, polished frontend, and automated ingestion.*

**16. Sync Bucket Optimization (Event Listeners vs Webhooks)**
*   **Solution:** Replaced static MinIO webhooks with a native Python MinIO Event Listener running as a Daemon thread in the worker. It listens for `s3:ObjectCreated:*` and instantly drops them into the Redis queue, offering true real-time zero-configuration ingestion.

**17. Manual "Sync Bucket" Background Worker & Diffing**
*   **Solution:** Built a `POST /sync_bucket` endpoint that triggers a background job to scan the MinIO bucket, diff against the DB, and ingest missing images. Wrapped it in a Redis lock (`setex`) to securely prevent duplicate concurrent syncs.

**18. Modern UI with ShadCN Components & Autoscroll**
*   **Solution:** Built the React frontend using `shadcn/ui` and `TailwindCSS` for a premium dark-mode aesthetic.
*   **Autoscroll:** Integrated `react-infinite-scroll-component` tied to standard page limits. As the user scrolls, it dynamically fetches subsequent pages of decreasing similarity index without loading spinners blocking the screen.

**19. .AI and .PDF Viewing & Direct Downloads**
*   **Solution:** Browsers cannot natively render `.ai` files. Modified the preprocessor to render the first page of PDFs and AI files at 300 DPI as a lightweight [.png](file:///c:/Users/ACHAL.TRIVEDI/Downloads/InHouse-Indexed%20Search/frontend/patterns-logo.png) thumbnail. The search API serves this thumbnail to the UI's `<img>` tag, while the "Download" button safely provides a [presigned_download_url](file:///c:/Users/ACHAL.TRIVEDI/Downloads/InHouse-Indexed%20Search/utils/minio_utils.py#243-255) direct to the original S3 `.ai` file.

**20. Data API: Showcasing Indexed Assets & Live Status**
*   **Solution:** Created a `/data` router page mapped to a `GET /api/gallery` endpoint. Displays everything in the DB in a paginated table. 
*   **Real-time flair:** The endpoint dynamically checks the Redis `started_job_registry` to find items actively being processed, overlaying a "Processing" spinner on them in the UI until they are fully embedded.

**21. OMS App Integration & Total Count (Idea Discarded / Deprioritized)**
*   **Solution:** Evaluated local OMS integration but discarded it to strictly focus on making the microservice highly cohesive and decoupled. Total bucket count logic was swapped out in favor of tracking Total *Indexed* Count via DB queries for performance.

---
*Generated for 15-20 week project management reporting.*
