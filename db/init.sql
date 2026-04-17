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
