FROM python:3.11-slim

WORKDIR /app

# System deps required by opencv-python-headless
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch separately using the official wheel index (faster download)
# We use --no-cache-dir to keep image size small, but Docker layer caching handles rebuilds
RUN pip install --no-cache-dir torch>=2.0.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install Python dependencies (rest of them)
COPY requirements.txt .
# Remove torch from requirements.txt to avoid double install (or let pip skipping handle it)
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download CLIP model during build (avoids ~600MB download on first startup)
# This prevents health check timeouts and container restart loops
RUN python -c "\
    from transformers import CLIPVisionModel, CLIPProcessor; \
    CLIPVisionModel.from_pretrained('openai/clip-vit-base-patch32', use_safetensors=True); \
    CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32'); \
    print('CLIP model pre-downloaded successfully')"

# Copy application code
COPY . .

# Default command (overridden in docker-compose)
CMD ["python", "tools/run_worker.py"]
