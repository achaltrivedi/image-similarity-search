# ============================================================
# Multi-stage Dockerfile for Image Similarity API + Worker
# Optimized for minimal image size (~1.5GB vs 3.5GB)
# ============================================================

# ---------- Stage 1: Install dependencies ----------
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps for opencv-python-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (saves ~1.5GB vs full CUDA build)
# Only 'torch' is needed — torchvision and torchaudio are NOT used
RUN pip install --no-cache-dir --user \
    torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Pre-download CLIP model during build (~600MB, cached in Docker layer)
# Prevents health check timeouts and container restart loops on first boot
RUN python -c "\
    import sys; sys.path.insert(0, '/root/.local/lib/python3.11/site-packages'); \
    from transformers import CLIPVisionModel, CLIPProcessor; \
    CLIPVisionModel.from_pretrained('openai/clip-vit-base-patch32', use_safetensors=True); \
    CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32'); \
    print('CLIP model pre-downloaded successfully')"

# ---------- Stage 2: Runtime (lean) ----------
FROM python:3.11-slim

WORKDIR /app

# System deps (runtime only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy pre-downloaded HuggingFace model cache
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface

# Ensure pip-installed binaries are on PATH
ENV PATH=/root/.local/bin:$PATH

# Copy application code (respects .dockerignore)
COPY . .

# Default command (overridden per service in docker-compose)
CMD ["python", "tools/run_worker.py"]
