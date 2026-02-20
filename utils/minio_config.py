import os

# MinIO Configuration
# Default to localhost for local dev, but allow override for Docker
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")

# Public endpoint for browser-accessible presigned URLs
# Falls back to MINIO_ENDPOINT if not set (works for local dev)
MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_ENDPOINT", MINIO_ENDPOINT)

BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "image-similarity-test")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "super-secure-token-123")