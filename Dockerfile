# ============================================================
# Single multi-stage Dockerfile — API, Worker & Frontend
# Targets:  api  (used by 'app' and 'worker' services)
#           frontend  (used by 'frontend' service)
# ============================================================

# ────────────────────────────────────────────────────────────
# Stage 1: Python dependency builder
# ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS python-builder

WORKDIR /build

ENV PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/root/.local/lib/python3.11/site-packages \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/root/.cache/huggingface \
    TRANSFORMERS_CACHE=/root/.cache/huggingface/hub

# System deps for opencv-python-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (torch pulled from CPU-only index via requirements.txt)
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Pre-download CLIP model (~600MB, baked into image layer)
# Prevents health-check timeouts and restart loops on first boot
RUN python -c "\
import sys; \
print('Python:', sys.version); \
print('sys.path:', sys.path); \
from huggingface_hub import snapshot_download; \
snapshot_download(repo_id='openai/clip-vit-base-patch32', repo_type='model', ignore_patterns=['*.msgpack', '*.h5', 'flax_model*', 'tf_model*', 'rust_model*']); \
print('CLIP model pre-downloaded successfully')"

# ────────────────────────────────────────────────────────────
# Stage 2: API / Worker runtime  ← target: api
# ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS api

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages and model cache from builder
COPY --from=python-builder /root/.local /root/.local
COPY --from=python-builder /root/.cache/huggingface /root/.cache/huggingface

ENV HF_HOME=/root/.cache/huggingface \
    TRANSFORMERS_CACHE=/root/.cache/huggingface/hub

ENV PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/root/.local/lib/python3.11/site-packages \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy only application code needed for the API/Worker (excludes frontend/, nginx.conf)
COPY app.py .
COPY core/ core/
COPY utils/ utils/
COPY tools/ tools/
COPY db/ db/

# Default command — overridden per service in docker-compose
CMD ["python", "tools/run_worker.py"]

# ────────────────────────────────────────────────────────────
# Stage 3: Frontend Node build
# ────────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /app

# Copy only package files first for layer caching
COPY frontend/package*.json ./
RUN npm ci

# Copy the rest of the frontend source
COPY frontend/ .
RUN npm run build

# ────────────────────────────────────────────────────────────
# Stage 4: Frontend Nginx runtime  ← target: frontend
# ────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS frontend

COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
