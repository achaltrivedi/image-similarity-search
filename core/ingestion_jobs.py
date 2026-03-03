from __future__ import annotations

from urllib.parse import unquote_plus

from core.database import SessionLocal, ImageEmbedding
from core.embedding import ImageEmbedder
from core.preprocessor import ImagePreprocessor
from core.design_features import extract_design_features
from core.color_texture_features import extract_color_features, extract_texture_features
from utils.minio_config import BUCKET_NAME
from utils.minio_utils import SUPPORTED_IMAGE_EXTENSIONS, download_object, upload_object

_embedder: ImageEmbedder | None = None


def _get_embedder() -> ImageEmbedder:
    global _embedder
    if _embedder is None:
        print("Initializing worker embedder...")
        _embedder = ImageEmbedder()
    return _embedder


def _normalized_object_key(record: dict) -> str | None:
    raw_key = record.get("s3", {}).get("object", {}).get("key")
    if not raw_key:
        return None
    return unquote_plus(raw_key)


def process_minio_record(record: dict) -> dict:
    """Background job entrypoint for a single MinIO event record."""
    event_name = record.get("eventName", "")
    object_key = _normalized_object_key(record)

    if not object_key:
        return {"status": "skipped", "reason": "missing_object_key"}

    if event_name.startswith("s3:ObjectRemoved:"):
        db = SessionLocal()
        try:
            deleted_rows = db.query(ImageEmbedding).filter_by(object_key=object_key).delete()
            db.commit()
            print(f"[worker] Synchronized delete for {object_key}: removed={deleted_rows}")
            return {"status": "deleted", "object_key": object_key, "deleted_rows": deleted_rows}
        except Exception as e:
            db.rollback()
            print(f"[worker] Failed delete for {object_key}: {e}")
            raise
        finally:
            db.close()

    if not object_key.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS):
        return {"status": "skipped", "reason": "unsupported_extension", "object_key": object_key}
        
    # STOP INFINITE RECURSION: Do not process thumbnails
    if object_key.startswith(".thumbnails/"):
        return {"status": "skipped", "reason": "is_thumbnail", "object_key": object_key}

    # 1. Download image
    file_bytes = download_object(object_key)
    file_size = len(file_bytes)

    # 2. Preprocess (converts to RGB Image)
    image = ImagePreprocessor.process(file_bytes, object_key)
    
    # 3. Generate & Upload Thumbnail (if needed or for all)
    # We do it for all to have consistent fast previews
    try:
        thumb_bytes = ImagePreprocessor.create_thumbnail(image)
        if thumb_bytes:
            thumb_key = f".thumbnails/{object_key}.png"
            upload_object(thumb_key, thumb_bytes, content_type="image/png")
            print(f"[worker] Uploaded thumbnail: {thumb_key}")
    except Exception as e:
        print(f"[worker] Failed to create thumbnail: {e}")

    # 4. Generate Embeddings (CLIP + Design)
    embedder = _get_embedder()
    embedding = embedder.embed_images([image])
    embedding_list = embedding.cpu().numpy()[0].tolist()
    
    try:
        design_vec = extract_design_features(image)
        color_vec = extract_color_features(image)
        texture_vec = extract_texture_features(image)
    except Exception:
        design_vec = None
        color_vec = None
        texture_vec = None

    db = SessionLocal()
    try:
        existing = db.query(ImageEmbedding).filter_by(object_key=object_key).first()
        if existing:
            existing.embedding = embedding_list
            existing.design_embedding = design_vec
            existing.color_embedding = color_vec
            existing.texture_embedding = texture_vec
            existing.minio_metadata = {"file_size": file_size}
        else:
            db.add(ImageEmbedding(
                object_key=object_key,
                embedding=embedding_list,
                design_embedding=design_vec,
                color_embedding=color_vec,
                texture_embedding=texture_vec,
                minio_metadata={"file_size": file_size}
            ))
        db.commit()
        
        # Publish real-time event
        try:
            import json
            from redis import Redis
            from core.task_queue import REDIS_URL
            from utils.minio_utils import presigned_url, presigned_download_url
            import datetime
            
            r = Redis.from_url(REDIS_URL, decode_responses=True)
            
            filename = object_key.split("/")[-1] if "/" in object_key else object_key
            ext = filename.rsplit(".", 1)[-1].upper() if "." in filename else "—"
            
            # Format size
            size_bytes = file_size
            size_str = "Unknown"
            if size_bytes:
                k = 1024
                sizes = ["B", "KB", "MB", "GB"]
                i = 0
                s = float(size_bytes)
                while s >= k and i < len(sizes) - 1:
                    s /= k
                    i += 1
                size_str = f"{s:.1f} {sizes[i]}"
                
            thumb_url = None
            img_url = None
            dl_url = None
            try:
                thumb_key = f".thumbnails/{object_key}.png"
                thumb_url = presigned_url(thumb_key)
                if object_key.lower().endswith(('.ai', '.pdf')):
                    img_url = thumb_url
                else:
                    img_url = presigned_url(object_key)
                dl_url = presigned_download_url(object_key, filename)
            except Exception:
                pass
                
            # Fetch the actual ID of the inserted/updated row
            row_id = existing.id if existing else db.query(ImageEmbedding.id).filter_by(object_key=object_key).first()[0]
            
            payload = {
                "id": row_id,
                "object_key": object_key,
                "filename": filename,
                "type": ext,
                "size": size_str,
                "size_bytes": size_bytes,
                "status": "Done",
                "indexed_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "thumbnail_url": thumb_url,
                "image_url": img_url,
                "download_url": dl_url,
                "event_type": "new_item"
            }
            r.publish("gallery_updates", json.dumps(payload))
        except Exception as pub_e:
            print(f"[worker] Failed to publish WebSocket event: {pub_e}")

        print(f"[worker] Indexed/upserted {object_key}")
        return {"status": "indexed", "object_key": object_key}
    except Exception as e:
        db.rollback()
        print(f"[worker] Failed upsert for {object_key}: {e}")
        raise
    finally:
        db.close()
