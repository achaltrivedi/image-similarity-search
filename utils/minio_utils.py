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
