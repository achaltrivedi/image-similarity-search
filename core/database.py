import os
from sqlalchemy import Boolean, Float, create_engine, Column, Integer, String, DateTime, func, text
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
    color_embedding = Column(Vector(256), nullable=True)   # HSV color histogram (color)
    texture_embedding = Column(Vector(64), nullable=True)  # Grayscale histogram (texture)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    minio_metadata = Column(JSONB, nullable=True)

class SearchSettings(Base):
    __tablename__ = "search_settings"

    id = Column(Integer, primary_key=True, index=True)
    settings_key = Column(String, unique=True, nullable=False, default="search")
    default_results_per_page = Column(Integer, nullable=False, default=50)
    similarity_threshold = Column(Float, nullable=False, default=0.0)
    semantic_weight = Column(Float, nullable=False, default=0.55)
    design_weight = Column(Float, nullable=False, default=0.20)
    color_weight = Column(Float, nullable=False, default=0.15)
    texture_weight = Column(Float, nullable=False, default=0.10)
    enable_sub_part_localization = Column(Boolean, nullable=False, default=True)
    bounding_box_effect = Column(String, nullable=False, default="scanner")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

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
            # Force add columns if the table existed before they were added
            alter_sql = """
            ALTER TABLE image_embeddings 
            ADD COLUMN IF NOT EXISTS design_embedding vector(256),
            ADD COLUMN IF NOT EXISTS color_embedding vector(256),
            ADD COLUMN IF NOT EXISTS texture_embedding vector(64);
            """
            conn.execute(text(alter_sql))
            
            settings_sql = """
            CREATE TABLE IF NOT EXISTS search_settings (
                id SERIAL PRIMARY KEY,
                settings_key VARCHAR UNIQUE NOT NULL DEFAULT 'search',
                default_results_per_page INTEGER NOT NULL DEFAULT 50,
                similarity_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                semantic_weight DOUBLE PRECISION NOT NULL DEFAULT 0.55,
                design_weight DOUBLE PRECISION NOT NULL DEFAULT 0.20,
                color_weight DOUBLE PRECISION NOT NULL DEFAULT 0.15,
                texture_weight DOUBLE PRECISION NOT NULL DEFAULT 0.10,
                enable_sub_part_localization BOOLEAN NOT NULL DEFAULT TRUE,
                bounding_box_effect VARCHAR NOT NULL DEFAULT 'scanner',
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
            conn.execute(text(settings_sql))

            settings_alter_sql = """
            ALTER TABLE search_settings
            ADD COLUMN IF NOT EXISTS default_results_per_page INTEGER NOT NULL DEFAULT 50,
            ADD COLUMN IF NOT EXISTS similarity_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS semantic_weight DOUBLE PRECISION NOT NULL DEFAULT 0.55,
            ADD COLUMN IF NOT EXISTS design_weight DOUBLE PRECISION NOT NULL DEFAULT 0.20,
            ADD COLUMN IF NOT EXISTS color_weight DOUBLE PRECISION NOT NULL DEFAULT 0.15,
            ADD COLUMN IF NOT EXISTS texture_weight DOUBLE PRECISION NOT NULL DEFAULT 0.10,
            ADD COLUMN IF NOT EXISTS enable_sub_part_localization BOOLEAN NOT NULL DEFAULT TRUE,
            ADD COLUMN IF NOT EXISTS bounding_box_effect VARCHAR NOT NULL DEFAULT 'scanner',
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
            """
            conn.execute(text(settings_alter_sql))

            seed_settings_sql = """
            INSERT INTO search_settings (
                settings_key,
                default_results_per_page,
                similarity_threshold,
                semantic_weight,
                design_weight,
                color_weight,
                texture_weight,
                enable_sub_part_localization,
                bounding_box_effect
            )
            VALUES ('search', 50, 0.0, 0.55, 0.20, 0.15, 0.10, TRUE, 'scanner')
            ON CONFLICT (settings_key) DO NOTHING;
            """
            conn.execute(text(seed_settings_sql))

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

            # Create HNSW index for color embeddings
            index_sql_color = """
            CREATE INDEX IF NOT EXISTS idx_image_embeddings_color_vector 
            ON image_embeddings 
            USING hnsw (color_embedding vector_cosine_ops) 
            WITH (m = 16, ef_construction = 128);
            """
            conn.execute(text(index_sql_color))
            
            # Create HNSW index for texture embeddings
            index_sql_texture = """
            CREATE INDEX IF NOT EXISTS idx_image_embeddings_texture_vector 
            ON image_embeddings 
            USING hnsw (texture_embedding vector_cosine_ops) 
            WITH (m = 16, ef_construction = 128);
            """
            conn.execute(text(index_sql_texture))
            
            conn.commit()
    except Exception as e:
        print(f"Warning: Database column alteration or indexing failed: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
