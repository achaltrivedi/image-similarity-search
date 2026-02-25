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
        # Ensure the vector extension is installed
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            
            # Create HNSW index for high-performance search at 300k+ scale
            # vector_cosine_ops is used for cosine similarity (matching CLIP requirements)
            index_sql = """
            CREATE INDEX IF NOT EXISTS idx_image_embeddings_vector 
            ON image_embeddings 
            USING hnsw (embedding vector_cosine_ops) 
            WITH (m = 16, ef_construction = 128);
            """
            conn.execute(text(index_sql))
            
            # HNSW index for design embeddings (structural similarity)
            index_sql = """
            CREATE INDEX IF NOT EXISTS idx_image_embeddings_design_vector 
            ON image_embeddings 
            USING hnsw (design_embedding vector_cosine_ops) 
            WITH (m = 16, ef_construction = 128);
            """
            conn.execute(text(index_sql))
            conn.commit()
    except Exception as e:
        print(f"Warning: Database initialization step failed: {e}")

    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
