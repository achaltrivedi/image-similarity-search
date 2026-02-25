import sys
from pathlib import Path

# Ensure project root is importable when run from tools/ or repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env variables
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from core.database import init_db

if __name__ == "__main__":
    print(f"🔄 Initializing database at {PROJECT_ROOT}...")
    try:
        init_db()
        print("✅ Database tables and pgvector extension created successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
