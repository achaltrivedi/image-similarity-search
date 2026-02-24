-- This script runs automatically when PostgreSQL starts for the first time.
-- It creates the pgvector extension and the image_embeddings table.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS image_embeddings (
    id SERIAL PRIMARY KEY,
    object_key VARCHAR UNIQUE NOT NULL,
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    minio_metadata JSONB
);

-- HNSW index for fast cosine similarity search at scale
CREATE INDEX IF NOT EXISTS idx_image_embeddings_vector
ON image_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 128);

-- Index on object_key for fast lookups
CREATE INDEX IF NOT EXISTS idx_image_embeddings_object_key
ON image_embeddings (object_key);
