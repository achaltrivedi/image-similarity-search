import os
import io
import time
import sys
import argparse
from typing import List, Set, Tuple
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv

# Ensure project root is importable when run from tools/ or repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env")

from core.database import SessionLocal, ImageEmbedding
from core.embedding import ImageEmbedder
from core.preprocessor import ImagePreprocessor
from core.design_features import extract_design_features
from core.color_texture_features import extract_color_features, extract_texture_features
from utils.minio_utils import get_s3_client, SUPPORTED_IMAGE_EXTENSIONS
from utils.minio_config import BUCKET_NAME

# Configuration for large scale ingestion
BATCH_SIZE = 64  # Increased batch size for GPU efficiency
MAX_KEYS_PER_LIST = 1000  # S3 API limit per call

def get_existing_keys() -> Set[str]:
    """Retrieves all object keys already indexed in the database."""
    db = SessionLocal()
    try:
        # We only need the keys for comparison
        keys = db.query(ImageEmbedding.object_key).all()
        return {k[0] for k in keys}
    finally:
        db.close()

def process_batch(embedder: ImageEmbedder, batch_keys: List[str], batch_images: List[Image.Image], batch_sizes: List[int]) -> int:
    """Embeds and saves a batch of images."""
    if not batch_keys:
        return 0

    try:
        # Batch embedding (The big speedup)
        # embed_images expects a list of PIL Images
        embedding_tensor = embedder.embed_images(batch_images)
        embeddings_list = embedding_tensor.cpu().numpy().tolist()

        # Create DB objects with all embeddings
        db_objects = []
        for key, embedding, image, size in zip(batch_keys, embeddings_list, batch_images, batch_sizes):
            try:
                design_vec = extract_design_features(image)
                color_vec = extract_color_features(image)
                texture_vec = extract_texture_features(image)
            except Exception:
                design_vec = None
                color_vec = None
                texture_vec = None
                
            db_objects.append(ImageEmbedding(
                object_key=key,
                embedding=embedding,
                design_embedding=design_vec,
                color_embedding=color_vec,
                texture_embedding=texture_vec,
                minio_metadata={"file_size": size}
            ))
        
        save_batch_to_db(db_objects)
        return len(db_objects)
    except Exception as e:
        print(f"❌ Error processing batch of size {len(batch_keys)}: {e}")
        return 0

def save_batch_to_db(batch: List[ImageEmbedding]):
    """Saves a batch of records to the database."""
    db = SessionLocal()
    try:
        db.add_all(batch)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ Failed to save batch to DB: {e}")
        # If batch fail, try individual inserts to save what we can
        print("🔄 Attempting individual inserts for this batch...")
        for item in batch:
            try:
                # Merge instead of add to handle potential race conditions
                db.merge(item)
                db.commit()
            except:
                db.rollback()
    finally:
        db.close()

def batch_index_images(force_reindex: bool = False):
    print("=" * 60)
    print("🚀 STARTING GPU-ACCELERATED BATCH INDEXING")
    if force_reindex:
        print("⚠️  FORCE RE-INDEX ENABLED (Clearing existing DB records)")
        db = SessionLocal()
        try:
            db.query(ImageEmbedding).delete()
            db.commit()
            print("🗑️  Cleared existing database records for a fresh start.")
        except Exception as e:
            db.rollback()
            print(f"Failed to clear DB: {e}")
        finally:
            db.close()
    print("=" * 60)

    # 1. Initialize components
    s3 = get_s3_client()
    embedder = ImageEmbedder()
    
    if not force_reindex:
        existing_keys = get_existing_keys()
        print(f"📊 Found {len(existing_keys)} images already indexed.")
    else:
        existing_keys = set()
    
    print(f"📦 Target Bucket: {BUCKET_NAME}")
    print(f"⚡ Batch Size: {BATCH_SIZE}")

    # 2. Setup Pagination
    paginator = s3.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=BUCKET_NAME)

    current_batch_keys: List[str] = []
    current_batch_images: List[Image.Image] = []
    current_batch_sizes: List[int] = []
    
    total_processed = 0
    total_new = 0
    start_time = time.time()

    try:
        for page in page_iterator:
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']
                total_processed += 1

                # Skip if already exists (unless forced)
                if not force_reindex and key in existing_keys:
                    continue
                
                # Filter by extension
                if not key.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS):
                    continue
                
                # STOP RECURSION: Skip hidden thumbnail files
                if key.startswith(".thumbnails/"):
                    continue

                print(f"[{total_processed}] Downloading: {key}...", end='\r')
                
                try:
                    # Download image bytes
                    response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
                    file_bytes = response['Body'].read()

                    # Preprocess
                    image = ImagePreprocessor.process(file_bytes, key)
                    
                    # Add to batch buffers
                    current_batch_keys.append(key)
                    current_batch_images.append(image)
                    current_batch_sizes.append(len(file_bytes))

                    # --- THUMBNAIL GENERATION ---
                    try:
                        # We upload thumbnails immediately (not batched) to keep batch logic simple
                        # It adds network overhead but ensures thumbnails exist
                        thumb_bytes = ImagePreprocessor.create_thumbnail(image)
                        if thumb_bytes:
                            thumb_key = f".thumbnails/{key}.png"
                            s3.put_object(
                                Bucket=BUCKET_NAME,
                                Key=thumb_key,
                                Body=thumb_bytes,
                                ContentType="image/png"
                            )
                    except Exception as e:
                        print(f"⚠️ Thumbnail fail for {key}: {e}")
                    # ----------------------------

                    # Process batch if full
                    if len(current_batch_keys) >= BATCH_SIZE:
                        print(f"\n⚡ Processing batch of {len(current_batch_keys)} items...")
                        count = process_batch(embedder, current_batch_keys, current_batch_images, current_batch_sizes)
                        total_new += count
                        
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            print(f"✅ Committed batch. Total Indexed: {total_new} | Avg Speed: {total_new/elapsed:.2f} imgs/s")
                        
                        # Reset buffers
                        current_batch_keys = []
                        current_batch_images = []
                        current_batch_sizes = []

                except Exception as e:
                    print(f"\n⚠️ Error preparing {key}: {e}")
                    continue

        # Final batch commit
        if current_batch_keys:
            print(f"\n⚡ Processing final batch of {len(current_batch_keys)} items...")
            count = process_batch(embedder, current_batch_keys, current_batch_images, current_batch_sizes)
            total_new += count
            print(f"✅ Final batch committed.")

    except Exception as e:
        print(f"\n❌ Critical error during pagination: {e}")

    end_time = time.time()
    print("\n" + "=" * 60)
    print("🏁 BATCH INDEXING COMPLETE")
    print(f"Total Scanned: {total_processed}")
    print(f"Total Newly Indexed: {total_new}")
    print(f"Total Time: {(end_time - start_time):.2f}s")
    if total_new > 0 and (end_time - start_time) > 0:
        print(f"Overall Speed: {total_new / (end_time - start_time):.2f} images/second")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch Indexing Tool")
    parser.add_argument("--force", action="store_true", help="Force re-indexing of all images, even if they exist in DB.")
    args = parser.parse_args()
    
    batch_index_images(force_reindex=args.force)
