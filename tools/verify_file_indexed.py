
import sys
import argparse
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.database import SessionLocal, ImageEmbedding

def verify_file(filename: str):
    print(f"🔍 Verifying text index for: {filename}")
    
    db = SessionLocal()
    try:
        # Query for the object key
        # We query for partial match in case of nested paths, or exact match
        record = db.query(ImageEmbedding).filter(ImageEmbedding.object_key.like(f"%{filename}")).first()
        
        if record:
            print(f"✅ FOUND: {record.object_key}")
            print(f"   - ID: {record.id}")
            print(f"   - Embedding Length: {len(record.embedding)}")
            return True
        else:
            print(f"❌ NOT FOUND: {filename}")
            print("   Possible reasons:")
            print("   1. Webhook hasn't processed it yet (check worker logs)")
            print("   2. File extension not supported")
            print("   3. MinIO bucket event failed to fire")
            return False
            
    except Exception as e:
        print(f"⚠️ Error querying database: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify if a file is indexed.")
    parser.add_argument("filename", help="The filename or object key to check")
    args = parser.parse_args()
    
    verify_file(args.filename)
