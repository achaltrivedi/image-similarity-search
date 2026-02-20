import time
import boto3
from io import BytesIO
from PIL import Image
from utils.minio_config import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_PUBLIC_ENDPOINT,
    BUCKET_NAME
)

from botocore.client import Config

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

# Cached S3 clients (avoid creating a new boto3 client per request)
_s3_client = None
_s3_public_client = None

# Cached bucket key set (refreshed every 5 minutes)
_bucket_keys_cache = None
_bucket_keys_timestamp = 0
_BUCKET_CACHE_TTL = 300  # 5 minutes

def get_s3_client():
    """S3 client using internal endpoint (for backend operations: download, upload)."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            region_name="us-east-1",
            config=Config(signature_version='s3v4', s3={'addressing_style': 'path'})
        )
    return _s3_client

def get_public_s3_client():
    """S3 client using public endpoint (for generating browser-accessible presigned URLs)."""
    global _s3_public_client
    if _s3_public_client is None:
        _s3_public_client = boto3.client(
            "s3",
            endpoint_url=MINIO_PUBLIC_ENDPOINT,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            region_name="us-east-1",
            config=Config(signature_version='s3v4', s3={'addressing_style': 'path'})
        )
    return _s3_public_client

def get_bucket_keys() -> frozenset:
    """Return a cached set of ALL object keys in the bucket.

    Used for fast O(1) existence checks when filtering search results.
    Refreshes automatically every 5 minutes.
    """
    global _bucket_keys_cache, _bucket_keys_timestamp
    now = time.time()
    if _bucket_keys_cache is None or (now - _bucket_keys_timestamp) > _BUCKET_CACHE_TTL:
        s3 = get_s3_client()
        keys = set()
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=BUCKET_NAME):
            for obj in page.get("Contents", []):
                keys.add(obj["Key"])
        _bucket_keys_cache = frozenset(keys)
        _bucket_keys_timestamp = now
        print(f"🔄 Bucket key cache refreshed: {len(keys)} objects")
    return _bucket_keys_cache

def load_images_from_minio():
    """
    Returns:
        images: list[PIL.Image]
        image_keys: list[str]  (object names)
    """
    # Backwards-compatible: load all images (uses the new helpers)
    keys = list_image_keys()
    return load_images_by_keys(keys)


def _is_supported_key(key: str) -> bool:
    return key.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS)


def list_image_keys(prefix: str | None = None):
    """Return all supported image object keys in the configured bucket.

    Uses S3 pagination so nested/deep buckets are fully scanned.
    """
    s3 = get_s3_client()
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    paginate_kwargs = {"Bucket": BUCKET_NAME}
    if prefix:
        paginate_kwargs["Prefix"] = prefix

    for page in paginator.paginate(**paginate_kwargs):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if _is_supported_key(key):
                keys.append(key)

    return keys


def load_images_by_keys(keys: list[str]):
    """Load specific images by their object keys.

    Returns:
        images: list[PIL.Image]
        image_keys: list[str]
    """
    s3 = get_s3_client()

    images = []
    image_keys = []

    for key in keys:
        try:
            file_obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
            image_bytes = file_obj["Body"].read()
            img = Image.open(BytesIO(image_bytes)).convert("RGB")

            images.append(img)
            image_keys.append(key)
        except Exception as e:
            print(f"⚠️ Failed to load {key}: {e}")

    return images, image_keys
