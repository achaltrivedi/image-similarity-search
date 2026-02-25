import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

# Database URL (matching docker-compose defaults)
# Setup for local development vs docker
DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1") # 127.0.0.1 for running app locally (IPv4), 'db' for running inside docker
DB_PORT = os.getenv("POSTGRES_PORT", "5434")
DB_NAME = os.getenv("POSTGRES_DB", "vectordb")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Production-grade engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # Persistent connections
    max_overflow=10,       # Extra connections allowed during bursts
    pool_pre_ping=True,     # Liveness check (handles DB restarts)
    pool_recycle=3600      # Refresh connections hourly to prevent stales
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ImageEmbedding(Base):
    __tablename__ = "image_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    object_key = Column(String, unique=True, index=True, nullable=False)
    embedding = Column(Vector(768))  # CLIP ViT-B/32 (semantic)
    design_embedding = Column(Vector(256), nullable=True)  # Edge density grid (structural)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    minio_metadata = Column(JSONB, nullable=True)

def init_db():
    try:
        # 1. Ensure the vector extension is installed
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    except Exception as e:
        print(f"Warning: Failed to create vector extension: {e}")

    # 2. Create tables (only creates tables if they don't exist, does NOT alter them)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: Failed to create tables: {e}")

    # 3. Add any missing columns to existing tables (specifically design_embedding)
    #    and create high-performance generic indices
    try:
        with engine.connect() as conn:
            # Force add design_embedding if the table existed before it was added
            alter_sql = """
            ALTER TABLE image_embeddings 
            ADD COLUMN IF NOT EXISTS design_embedding vector(256);
            """
            conn.execute(text(alter_sql))

            # Create HNSW index for high-performance search at 300k+ scale (semantic)
            index_sql_clip = """
            CREATE INDEX IF NOT EXISTS idx_image_embeddings_vector 
            ON image_embeddings 
            USING hnsw (embedding vector_cosine_ops) 
            WITH (m = 16, ef_construction = 128);
            """
            conn.execute(text(index_sql_clip))
            
            # Create HNSW index for design embeddings (structural)
            index_sql_design = """
            CREATE INDEX IF NOT EXISTS idx_image_embeddings_design_vector 
            ON image_embeddings 
            USING hnsw (design_embedding vector_cosine_ops) 
            WITH (m = 16, ef_construction = 128);
            """
            conn.execute(text(index_sql_design))
            conn.commit()
    except Exception as e:
        print(f"Warning: Database column alteration or indexing failed: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
