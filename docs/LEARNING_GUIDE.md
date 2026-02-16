# Complete Guide: Docker + PostgreSQL + pgvector Migration

A comprehensive learning guide for understanding how we set up a scalable vector database using Docker, PostgreSQL, and pgvector.

---

## Table of Contents
1. [Core Concepts](#core-concepts)
2. [The Architecture](#the-architecture)
3. [Step-by-Step Workflow](#step-by-step-workflow)
4. [Docker Commands Explained](#docker-commands-explained)
5. [Troubleshooting Journey](#troubleshooting-journey)
6. [Best Practices](#best-practices)

---

## Core Concepts

### What is Docker?
**Docker** is a platform that packages applications and their dependencies into **containers**. Think of containers as lightweight, isolated environments that run consistently anywhere.

**Key Benefits:**
- **Consistency**: "Works on my machine" → "Works everywhere"
- **Isolation**: Database runs in its own environment, separate from your host machine
- **Easy Setup**: No manual PostgreSQL installation needed
- **Version Control**: Specify exact versions (e.g., `postgres:16`)

### What is pgvector?
**pgvector** is a PostgreSQL extension that adds support for **vector similarity search**.

**Why we need it:**
- Store high-dimensional vectors (our image embeddings are 768 dimensions)
- Perform fast similarity searches using distance metrics (cosine, L2, inner product)
- Leverage PostgreSQL's ACID properties for vector data

**Example:**
```sql
-- Store a 768-dimensional vector
INSERT INTO image_embeddings (object_key, embedding) 
VALUES ('img1.png', '[0.1, 0.2, 0.3, ...]');

-- Find similar vectors using cosine distance
SELECT object_key, embedding <=> '[query_vector]' AS distance
FROM image_embeddings
ORDER BY distance
LIMIT 5;
```

### Why Migrate from FAISS to PostgreSQL?

| Aspect | FAISS (Before) | PostgreSQL + pgvector (After) |
|--------|----------------|-------------------------------|
| **Storage** | Local files | Database (persistent, transactional) |
| **Scalability** | Single machine | Can scale horizontally |
| **Concurrency** | File locks, risky | Database handles it |
| **Backup** | Manual file copies | Standard DB backup tools |
| **Production** | Not recommended | Industry standard |

---

## The Architecture

### Before Migration (FAISS)
```
┌─────────────────────────────────────┐
│         FastAPI Application         │
│  ┌──────────────┐  ┌──────────────┐ │
│  │ FaissIndex   │  │ MetadataStore│ │
│  │ (in-memory)  │  │ (JSON file)  │ │
│  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────┘
         ↓                    ↓
  faiss_index.bin    index_metadata.json
```

**Problems:**
- Data lost if app crashes
- Can't run multiple app instances
- No transactional guarantees

### After Migration (PostgreSQL + pgvector)
```
┌─────────────────────────────────────┐
│         FastAPI Application         │
│  ┌──────────────────────────────┐   │
│  │   SQLAlchemy ORM             │   │
│  │   (database.py)              │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
                ↓
         Network (port 5433)
                ↓
┌─────────────────────────────────────┐
│      Docker Container               │
│  ┌──────────────────────────────┐   │
│  │  PostgreSQL 16 + pgvector    │   │
│  │  ┌────────────────────────┐  │   │
│  │  │  image_embeddings      │  │   │
│  │  │  - id                  │  │   │
│  │  │  - object_key          │  │   │
│  │  │  - embedding (vector)  │  │   │
│  │  └────────────────────────┘  │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
                ↓
         Docker Volume
    (postgres_data - persistent storage)
```

**Benefits:**
- Data persists even if container restarts
- Multiple apps can connect simultaneously
- ACID transactions ensure data integrity

---

## Step-by-Step Workflow

### Phase 1: Docker Setup

#### 1.1 Create `docker-compose.yml`
This file defines our database service:

```yaml
version: '3.8'

services:
  db:
    image: pgvector/pgvector:pg16  # PostgreSQL 16 with pgvector pre-installed
    container_name: vector_db       # Name for easy reference
    environment:
      POSTGRES_USER: admin          # Database username
      POSTGRES_PASSWORD: password   # Database password
      POSTGRES_DB: vectordb         # Database name
    ports:
      - "5433:5432"                 # Host:Container port mapping
    volumes:
      - postgres_data:/var/lib/postgresql/data  # Persistent storage
    restart: always                 # Auto-restart on failure

volumes:
  postgres_data:  # Named volume for data persistence
```

**Key Concepts:**
- **Image**: Pre-built container template (like a class in OOP)
- **Container**: Running instance of an image (like an object)
- **Port Mapping**: `5433:5432` means "host port 5433 → container port 5432"
- **Volume**: Persistent storage that survives container deletion

#### 1.2 Start the Database
```bash
docker-compose up -d db
```

**What happens:**
1. Docker pulls the `pgvector/pgvector:pg16` image (if not cached)
2. Creates a container named `vector_db`
3. Creates a volume `postgres_data` for persistence
4. Starts PostgreSQL inside the container
5. Maps port 5433 on your machine to port 5432 in the container

**Verify it's running:**
```bash
docker ps
# Shows running containers

docker logs vector_db
# Shows PostgreSQL startup logs
```

### Phase 2: Database Configuration

#### 2.1 Create `database.py`
This file handles database connections using SQLAlchemy ORM:

```python
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
from pgvector.sqlalchemy import Vector

# Connection string
DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
DB_PORT = os.getenv("POSTGRES_PORT", "5433")  # Our custom port
DB_NAME = os.getenv("POSTGRES_DB", "vectordb")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
# Example: postgresql://admin:password@127.0.0.1:5433/vectordb

# Create engine (connection pool)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Define table schema
class ImageEmbedding(Base):
    __tablename__ = "image_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    object_key = Column(String, unique=True, index=True, nullable=False)
    embedding = Column(Vector(768))  # 768-dimensional vector
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Initialize database
def init_db():
    Base.metadata.create_all(bind=engine)
```

**Key Concepts:**
- **ORM (Object-Relational Mapping)**: Write Python code instead of SQL
- **Engine**: Manages database connections
- **Session**: Handles transactions
- **Vector(768)**: pgvector column type for 768-dimensional vectors

#### 2.2 Create Tables
```bash
# Inside Docker container
docker exec vector_db psql -U admin -d vectordb -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker exec vector_db psql -U admin -d vectordb -c "
CREATE TABLE IF NOT EXISTS image_embeddings (
    id SERIAL PRIMARY KEY,
    object_key TEXT UNIQUE NOT NULL,
    embedding vector(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);"
```

**What this does:**
1. Enables the `vector` extension
2. Creates the `image_embeddings` table
3. `SERIAL` = auto-incrementing integer
4. `vector(768)` = pgvector column for embeddings

### Phase 3: Data Migration

#### 3.1 The Challenge: Port Conflict
**Problem:** Your local PostgreSQL service was running on port 5432, blocking access to the Docker container.

**How we discovered it:**
```bash
netstat -ano | findstr :5432
# Output showed TWO processes listening on 5432!
```

**Solution:** Changed Docker port mapping to 5433 to avoid conflict.

#### 3.2 Migration Script (`migrate_to_pg.py`)
```python
import json
import faiss
import numpy as np

# Load existing FAISS data
index = faiss.read_index("storage/index.faiss")  # 21 vectors
with open("storage/metadata.json") as f:
    metadata = json.load(f)  # 21 object keys

# Generate SQL INSERT statements
with open("migration_inserts.sql", "w") as f:
    for i in range(index.ntotal):
        vector = index.reconstruct(i)  # Get vector from FAISS
        key = metadata[i]
        
        # Convert numpy array to PostgreSQL vector format
        vector_str = "[" + ",".join(map(str, vector.tolist())) + "]"
        
        # Generate SQL
        sql = f"INSERT INTO image_embeddings (object_key, embedding) VALUES ('{key}', '{vector_str}') ON CONFLICT (object_key) DO NOTHING;\n"
        f.write(sql)
```

**Why generate SQL instead of using Python?**
- We had a port conflict preventing direct Python connection
- SQL file can be piped directly into the Docker container
- More portable and debuggable

#### 3.3 Execute Migration
```bash
# Pipe SQL file into Docker container
type migration_inserts.sql | docker exec -i vector_db psql -U admin -d vectordb

# Verify
docker exec vector_db psql -U admin -d vectordb -c "SELECT COUNT(*) FROM image_embeddings;"
# Result: 18 (some duplicates were skipped due to UNIQUE constraint)
```

**What happened:**
1. Read SQL file from host machine
2. Pipe it into the container's `psql` command
3. PostgreSQL executes all INSERT statements
4. `ON CONFLICT DO NOTHING` prevents duplicate errors

### Phase 4: Application Updates

#### 4.1 Update `app.py` - Search Endpoint
**Before (FAISS):**
```python
query_embedding = embedder.embed_images([image])
query_np = query_embedding.cpu().numpy()
scores, indices = faiss_index.search(query_np, top_k)

for idx, score in zip(indices, scores):
    key = metadata.get(idx)
    # ...
```

**After (PostgreSQL):**
```python
query_embedding = embedder.embed_images([image])
query_vector = query_embedding.cpu().numpy()[0].tolist()

db = SessionLocal()
results_query = db.query(
    ImageEmbedding.object_key,
    ImageEmbedding.embedding.cosine_distance(query_vector).label('distance')
).order_by('distance').limit(top_k)

for row in results_query:
    key = row.object_key
    similarity = 1 - row.distance  # Convert distance to similarity
    # ...
```

**Key Differences:**
- FAISS: In-memory index search
- PostgreSQL: Database query with vector similarity operator (`<=>`)
- FAISS returns indices, PostgreSQL returns actual data

#### 4.2 Update Webhook Endpoint
**Before:** Used `IngestionService` to update FAISS index and JSON file

**After:** Direct database insert
```python
embedding_np = embedder.embed_images([image])[0]

db = SessionLocal()
db_obj = ImageEmbedding(
    object_key=object_key,
    embedding=embedding_np.tolist()
)
db.add(db_obj)
db.commit()
```

---

## Docker Commands Explained

### Essential Commands

```bash
# Start services defined in docker-compose.yml
docker-compose up -d
# -d = detached mode (runs in background)

# Stop and remove containers
docker-compose down
# Keeps volumes (data persists)

# Stop and remove containers + volumes
docker-compose down -v
# WARNING: Deletes all data!

# View running containers
docker ps
# Shows: container ID, image, status, ports

# View all containers (including stopped)
docker ps -a

# View logs
docker logs vector_db
docker logs -f vector_db  # Follow mode (live updates)

# Execute command inside container
docker exec vector_db psql -U admin -d vectordb -c "SELECT COUNT(*) FROM image_embeddings;"
# docker exec <container> <command>

# Interactive shell inside container
docker exec -it vector_db bash
# -i = interactive, -t = terminal

# Copy files to/from container
docker cp file.txt vector_db:/tmp/file.txt  # Host → Container
docker cp vector_db:/tmp/file.txt ./file.txt  # Container → Host

# View port mappings
docker port vector_db
# Shows: 5432/tcp -> 0.0.0.0:5433

# Restart container
docker restart vector_db

# Remove container
docker rm vector_db
# Must stop first or use -f flag

# View volumes
docker volume ls

# Inspect volume
docker volume inspect postgres_data
```

### Debugging Commands

```bash
# Check if PostgreSQL is accepting connections
docker exec vector_db pg_isready -U admin

# View PostgreSQL configuration
docker exec vector_db cat /var/lib/postgresql/data/postgresql.conf

# Check disk usage
docker exec vector_db df -h

# View running processes inside container
docker exec vector_db ps aux
```

---

## Troubleshooting Journey

### Issue 1: Port Conflict
**Symptom:**
```
psycopg2.OperationalError: connection to server at "127.0.0.1", port 5432 failed: 
FATAL: password authentication failed for user "admin"
```

**Diagnosis:**
```bash
netstat -ano | findstr :5432
# Output: TWO processes on port 5432!
```

**Root Cause:** Local PostgreSQL service was intercepting connections

**Solution:**
1. Changed Docker port mapping: `5432:5432` → `5433:5432`
2. Updated `database.py`: `DB_PORT = "5433"`
3. Restarted Docker container

**Lesson:** Always check for port conflicts when running databases locally

### Issue 2: Unicode Encoding Error
**Symptom:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680' in position 0
```

**Root Cause:** Windows console doesn't support emoji characters (🚀, 📦, etc.)

**Solution:** Removed all emojis from print statements

**Lesson:** Keep console output ASCII-safe for cross-platform compatibility

### Issue 3: Missing Dependencies
**Symptom:**
```
ModuleNotFoundError: No module named 'boto3'
```

**Solution:** Added `boto3>=1.26.0` to `requirements.txt` and ran `pip install -r requirements.txt`

**Lesson:** Always update requirements.txt when adding new imports

---

## Best Practices

### 1. Environment Variables
```python
# Good: Use environment variables for configuration
DB_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")

# Bad: Hardcoded values
DB_HOST = "127.0.0.1"
```

### 2. Connection Pooling
SQLAlchemy automatically manages connection pools:
```python
engine = create_engine(DATABASE_URL)
# Reuses connections instead of creating new ones each time
```

### 3. Always Close Database Sessions
```python
db = SessionLocal()
try:
    # Do database operations
    db.commit()
except Exception as e:
    db.rollback()
finally:
    db.close()  # IMPORTANT!
```

### 4. Use Volumes for Persistence
```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
```
Without volumes, data is lost when container is removed!

### 5. Index Your Vectors
For production with many vectors:
```sql
CREATE INDEX ON image_embeddings USING hnsw (embedding vector_cosine_ops);
```
This speeds up similarity searches significantly.

---

## Quick Reference

### Connection Flow
```
Your App (Python)
    ↓
SQLAlchemy Engine
    ↓
psycopg2 (PostgreSQL driver)
    ↓
Network (127.0.0.1:5433)
    ↓
Docker Port Mapping (5433 → 5432)
    ↓
PostgreSQL in Container (port 5432)
    ↓
pgvector Extension
    ↓
Data on Disk (Docker Volume)
```

### File Structure
```
InHouse-Indexed Search/
├── docker-compose.yml      # Docker service definition
├── database.py             # SQLAlchemy models & connection
├── app.py                  # FastAPI application
├── migrate_to_pg.py        # Migration script
├── requirements.txt        # Python dependencies
└── storage/
    ├── index.faiss         # Old FAISS index (deprecated)
    └── metadata.json       # Old metadata (deprecated)
```

---

## Summary

**What We Accomplished:**
1. ✅ Set up PostgreSQL with pgvector in Docker
2. ✅ Migrated 18 vectors from FAISS to PostgreSQL
3. ✅ Updated application to use database for vector search
4. ✅ Resolved port conflicts and environment issues
5. ✅ Created a production-ready, scalable architecture

**Key Takeaways:**
- Docker provides isolated, reproducible environments
- pgvector extends PostgreSQL with vector similarity search
- Always check for port conflicts when running local services
- Use environment variables for configuration
- Database persistence requires volumes

**Next Steps for Learning:**
- Explore PostgreSQL query optimization
- Learn about database indexing strategies (HNSW, IVFFlat)
- Study Docker networking and multi-container setups
- Practice writing database migrations
- Understand ACID properties and transactions

---

Happy Learning! 🎓
