"""
Cleanup stale database entries.

Removes image embeddings from PostgreSQL where the object_key
no longer exists in the configured MinIO/S3 bucket.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is importable when run from tools/ or repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env")

from core.database import SessionLocal, ImageEmbedding, init_db
from utils.minio_utils import get_bucket_keys


def cleanup_stale_entries(dry_run: bool = False):
    """Delete DB rows whose object_key is not present in the bucket.

    Args:
        dry_run: If True, only report what would be deleted without deleting.
    """
    print("🔍 Fetching all object keys from bucket...")
    bucket_keys = get_bucket_keys()
    print(f"   Bucket contains {len(bucket_keys)} objects")

    init_db()
    db = SessionLocal()
    try:
        all_entries = db.query(ImageEmbedding).all()
        print(f"   Database contains {len(all_entries)} indexed entries")

        stale = [e for e in all_entries if e.object_key not in bucket_keys]

        if not stale:
            print("\n✅ No stale entries found. Database is clean!")
            return

        print(f"\n⚠️  Found {len(stale)} stale entries (not in bucket):")
        for entry in stale:
            print(f"   - {entry.object_key}")

        if dry_run:
            print(f"\n🔒 DRY RUN: No entries were deleted. "
                  f"Run without --dry-run to delete {len(stale)} entries.")
            return

        # Delete stale entries
        for entry in stale:
            db.delete(entry)
        db.commit()

        remaining = db.query(ImageEmbedding).count()
        print(f"\n✅ Deleted {len(stale)} stale entries. {remaining} valid entries remain.")

    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Remove stale DB entries not found in bucket")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be deleted without actually deleting")
    args = parser.parse_args()
    cleanup_stale_entries(dry_run=args.dry_run)
