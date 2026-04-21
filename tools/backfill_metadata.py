from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

if os.getenv("POSTGRES_HOST") == "db":
    os.environ["POSTGRES_HOST"] = "127.0.0.1"
if os.getenv("POSTGRES_PORT") == "5432":
    os.environ["POSTGRES_PORT"] = "5433"
if os.getenv("MINIO_ENDPOINT") == "http://minio:9000":
    os.environ["MINIO_ENDPOINT"] = "http://localhost:9000"

from core.database import ImageEmbedding, SessionLocal
from core.image_metadata import extract_image_metadata
from core.preprocessor import ImagePreprocessor
from utils.minio_utils import download_object


def backfill_metadata(limit: int | None = None, dry_run: bool = False) -> dict:
    db = SessionLocal()
    processed = 0
    updated = 0
    failed = 0

    try:
        query = db.query(ImageEmbedding).order_by(ImageEmbedding.id)
        if limit:
            query = query.limit(limit)

        for row in query:
            processed += 1
            try:
                file_bytes = download_object(row.object_key)
                image = ImagePreprocessor.process(file_bytes, row.object_key)
                metadata = extract_image_metadata(image, row.object_key, len(file_bytes))
                if dry_run:
                    print(f"[dry-run] {row.object_key}: {metadata}")
                else:
                    row.minio_metadata = metadata
                    updated += 1
            except Exception as exc:
                failed += 1
                print(f"[metadata] failed {row.object_key}: {exc}")

        if dry_run:
            db.rollback()
        else:
            db.commit()

        return {"processed": processed, "updated": updated, "failed": failed}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill image metadata used by precision ranking.")
    parser.add_argument("--limit", type=int, default=None, help="Optional number of rows to process.")
    parser.add_argument("--dry-run", action="store_true", help="Print metadata without saving.")
    args = parser.parse_args()
    print(backfill_metadata(limit=args.limit, dry_run=args.dry_run))
