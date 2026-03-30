# ============================================================
# Single multi-stage Dockerfile — API, Worker & Frontend
# Targets:  api  (used by 'app' and 'worker' services)
#           frontend  (used by 'frontend' service)
# ============================================================

# ────────────────────────────────────────────────────────────
# Stage 1: ONNX Model Exporter (uses PyTorch temporarily)
# ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS onnx-exporter

WORKDIR /export

ARG HF_TOKEN
ENV HF_TOKEN=${HF_TOKEN}

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/root/.cache/huggingface \
    TRANSFORMERS_CACHE=/root/.cache/huggingface/hub

# Install PyTorch (CPU) + export dependencies — only needed for conversion
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu \
    torch>=2.0.0 \
    transformers>=4.36.0 \
    onnx>=1.15.0 \
    onnxruntime>=1.17.0 \
    safetensors>=0.4.0 \
    Pillow>=10.0.0

# Copy only what the export script needs
COPY utils/config.py utils/config.py
COPY tools/export_clip_onnx.py tools/export_clip_onnx.py

# Run the export — produces models/clip-vit-base-patch32.onnx
RUN python tools/export_clip_onnx.py

# ────────────────────────────────────────────────────────────
# Stage 2: Python dependency builder (lightweight, no PyTorch)
# ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS python-builder

WORKDIR /build

ARG HF_TOKEN
ENV HF_TOKEN=${HF_TOKEN}

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

# Install Python dependencies (onnxruntime, NOT torch)
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# ────────────────────────────────────────────────────────────
# Stage 3: API / Worker runtime  ← target: api
# ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS api

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=python-builder /root/.local /root/.local

# Copy the exported ONNX model from the exporter stage
COPY --from=onnx-exporter /export/models /app/models

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
# Stage 4: Frontend Node build
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
# Stage 5: Frontend Nginx runtime  ← target: frontend
# ────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS frontend

COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
