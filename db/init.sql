-- This script runs automatically when PostgreSQL starts for the first time.
-- It creates the pgvector extension and the image_embeddings table.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS image_embeddings (
    id SERIAL PRIMARY KEY,
    object_key VARCHAR UNIQUE NOT NULL,
    embedding vector(768),            -- CLIP (Semantic)
    design_embedding vector(256),     -- Edge density (Structural)
    color_embedding vector(256),      -- HSV Histogram (Color)
    texture_embedding vector(64),     -- Grayscale Histogram (Texture)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    minio_metadata JSONB
);

-- HNSW index for fast CLIP cosine similarity search at scale
CREATE INDEX IF NOT EXISTS idx_image_embeddings_vector
ON image_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 128);

-- HNSW index for fast design (structural) similarity search
CREATE INDEX IF NOT EXISTS idx_image_embeddings_design_vector
ON image_embeddings
USING hnsw (design_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 128);

-- HNSW index for fast color similarity search
CREATE INDEX IF NOT EXISTS idx_image_embeddings_color_vector
ON image_embeddings
USING hnsw (color_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 128);

-- HNSW index for fast texture similarity search
CREATE INDEX IF NOT EXISTS idx_image_embeddings_texture_vector
ON image_embeddings
USING hnsw (texture_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 128);

-- Index on object_key for fast lookups (redundant but kept for explicit clarity)
CREATE INDEX IF NOT EXISTS idx_image_embeddings_object_key
ON image_embeddings (object_key);
