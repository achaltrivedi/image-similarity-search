# Quick Fix for Local PostgreSQL Conflict

## Problem
Your local PostgreSQL service is running on port 5432, preventing the app from connecting to the Docker container.

## Solution Options

### Option 1: Stop Local PostgreSQL Service (Recommended for Development)
```powershell
# Stop the local PostgreSQL service
net stop postgresql-x64-16  # or whatever your service name is

# Then run your app
uvicorn app:app --reload
```

### Option 2: Change Docker Port Mapping
Edit `docker-compose.yml` to use a different port:
```yaml
ports:
  - "5433:5432"  # Map to 5433 on host instead
```

Then update `database.py`:
```python
DB_PORT = os.getenv("POSTGRES_PORT", "5433")
```

### Option 3: Run App Inside Docker (Best for Production)
Create a Dockerfile for your app and add it to docker-compose.yml

## Quick Test
To verify the Docker database is accessible:
```bash
docker exec vector_db psql -U admin -d vectordb -c "SELECT COUNT(*) FROM image_embeddings;"
```

This should return 18 records.
