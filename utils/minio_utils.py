import time
from io import BytesIO
from datetime import timedelta
from urllib.parse import urlparse

from PIL import Image
from minio import Minio
from minio.error import S3Error

from utils.minio_config import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_PUBLIC_ENDPOINT,
    BUCKET_NAME
)

SUPPORTED_IMAGE_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".tif",
    ".tiff",
    ".bmp",
    ".webp",
    ".ai",
)

# Cached MinIO clients (avoid creating a new client per request)
_minio_client = None
_minio_public_client = None

# Cached bucket key set (refreshed every 5 minutes)
_bucket_keys_cache = None
_bucket_keys_timestamp = 0
_BUCKET_CACHE_TTL = 300  # 5 minutes


def _parse_endpoint(endpoint_url: str):
    """Parse an endpoint URL into (host:port, secure) for minio-py."""
    parsed = urlparse(endpoint_url)
    host = parsed.hostname or "localhost"
    port = parsed.port
    secure = parsed.scheme == "https"
    endpoint = f"{host}:{port}" if port else host
    return endpoint, secure


def get_minio_client() -> Minio:
    """MinIO client using internal endpoint (for backend operations: download, upload)."""
    global _minio_client
    if _minio_client is None:
        endpoint, secure = _parse_endpoint(MINIO_ENDPOINT)
        _minio_client = Minio(
            endpoint,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=secure,
        )
    return _minio_client


def get_public_minio_client() -> Minio:
    """MinIO client using public endpoint (for generating browser-accessible presigned URLs)."""
    global _minio_public_client
    if _minio_public_client is None:
        endpoint, secure = _parse_endpoint(MINIO_PUBLIC_ENDPOINT)
        _minio_public_client = Minio(
            endpoint,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=secure,
        )
    return _minio_public_client


# -----------------------------------------------
# Backwards-compatible aliases (drop-in for old boto3 callers)
# -----------------------------------------------
def get_s3_client():
    """Alias for get_minio_client() — keeps old imports working."""
    return get_minio_client()

def get_public_s3_client():
    """Alias for get_public_minio_client() — keeps old imports working."""
    return get_public_minio_client()


def get_bucket_keys() -> frozenset:
    """Return a cached set of ALL object keys in the bucket.

    Used for fast O(1) existence checks when filtering search results.
    Refreshes automatically every 5 minutes.
    """
    global _bucket_keys_cache, _bucket_keys_timestamp
    now = time.time()
    if _bucket_keys_cache is None or (now - _bucket_keys_timestamp) > _BUCKET_CACHE_TTL:
        client = get_minio_client()
        keys = set()
        for obj in client.list_objects(BUCKET_NAME, recursive=True):
            keys.add(obj.object_name)
        _bucket_keys_cache = frozenset(keys)
        _bucket_keys_timestamp = now
        print(f"🔄 Bucket key cache refreshed: {len(keys)} objects")
    return _bucket_keys_cache


def list_image_keys(prefix: str | None = None):
    """Return all supported image object keys in the configured bucket.

    Uses MinIO's native recursive listing — no pagination boilerplate needed.
    """
    client = get_minio_client()
    keys = []
    for obj in client.list_objects(BUCKET_NAME, prefix=prefix or "", recursive=True):
        key = obj.object_name
        if _is_supported_key(key):
            keys.append(key)
    return keys


def load_images_from_minio():
    """
    Returns:
        images: list[PIL.Image]
        image_keys: list[str]  (object names)
    """
    keys = list_image_keys()
    return load_images_by_keys(keys)


def _is_supported_key(key: str) -> bool:
    return key.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS)


def load_images_by_keys(keys: list[str]):
    """Load specific images by their object keys.

    Returns:
        images: list[PIL.Image]
        image_keys: list[str]
    """
    client = get_minio_client()

    images = []
    image_keys = []

    for key in keys:
        try:
            response = client.get_object(BUCKET_NAME, key)
            image_bytes = response.read()
            response.close()
            response.release_conn()
            img = Image.open(BytesIO(image_bytes)).convert("RGB")

            images.append(img)
            image_keys.append(key)
        except Exception as e:
            print(f"⚠️ Failed to load {key}: {e}")

    return images, image_keys


# -----------------------------------------------
# Convenience helpers for common S3 operations
# -----------------------------------------------

def download_object(key: str) -> bytes:
    """Download an object and return its bytes."""
    client = get_minio_client()
    response = client.get_object(BUCKET_NAME, key)
    data = response.read()
    response.close()
    response.release_conn()
    return data


def upload_object(key: str, data: bytes, content_type: str = "application/octet-stream"):
    """Upload bytes as an object."""
    client = get_minio_client()
    client.put_object(
        BUCKET_NAME,
        key,
        BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def object_exists(key: str) -> bool:
    """Check if an object exists in the bucket."""
    client = get_minio_client()
    try:
        client.stat_object(BUCKET_NAME, key)
        return True
    except S3Error:
        return False


def presigned_url(key: str, expires: int = 3600, response_headers: dict | None = None) -> str:
    """Generate a presigned GET URL using the public endpoint."""
    client = get_public_minio_client()
    extra = {}
    if response_headers:
        from minio.helpers import ObjectWriteResult
        from urllib.parse import urlencode
        # minio-py supports response headers via extra_query_params
        extra["extra_query_params"] = response_headers
    return client.presigned_get_object(
        BUCKET_NAME,
        key,
        expires=timedelta(seconds=expires),
        **extra,
    )


def presigned_download_url(key: str, filename: str, expires: int = 3600) -> str:
    """Generate a presigned GET URL that forces browser download."""
    from urllib.parse import quote
    client = get_public_minio_client()
    return client.presigned_get_object(
        BUCKET_NAME,
        key,
        expires=timedelta(seconds=expires),
        response_headers={
            "response-content-disposition": f'attachment; filename="{quote(filename)}"'
        },
    )


def list_all_objects(prefix: str = ""):
    """Iterate over all objects in the bucket. Yields minio Object items."""
    client = get_minio_client()
    return client.list_objects(BUCKET_NAME, prefix=prefix, recursive=True)
