# 📊 Database & Logs Management Guide

This guide explains how to monitor, query, and maintain your Image Similarity Service using Docker Desktop and PostgreSQL.

---

## 🕒 1. Monitoring Logs
Monitoring logs is essential during the **Initial Ingestion (Batch Indexing)** to ensure everything is running smoothly.

### **Via Docker Desktop (GUI)**
1. Open **Docker Desktop**.
2. Go to the **Containers** tab.
3. Click on the container project (e.g., `inhouse-indexed-search`).
4. Click on **`app`** (for FastAPI logs) or **`vector_db`** (for Database logs).
5. The **Logs** tab will show you real-time activity (embeddings being generated, search queries, etc.).

### **Via Terminal (CLI)**
```powershell
# See logs for the entire project
docker-compose logs -f

# See logs only for the database
docker logs -f vector_db
```

---

## 🛠️ 2. Accessing the Database (PSQL)

### **The "Exec" Method (Easiest)**
1. In Docker Desktop, click on the **`vector_db`** container.
2. Click the **Exec** tab at the top.
3. Type the following and press Enter:
   ```bash
   psql -U admin -d vectordb
   ```

### **The Terminal Method**
```powershell
docker exec -it vector_db psql -U admin -d vectordb
```

---

## 🔍 3. Essential SQL Queries

Once inside `psql`, use these queries to manage your data:

### **General Tracking**
```sql
-- 1. Count total images indexed
SELECT count(*) FROM image_embeddings;

-- 2. View the 5 most recently indexed images
SELECT id, object_key, created_at 
FROM image_embeddings 
ORDER BY created_at DESC 
LIMIT 5;

-- 3. Check if a specific file exists in the index
SELECT id, object_key 
FROM image_embeddings 
WHERE object_key LIKE '%filename_part%';
```

### **Scalability & Index Monitoring**
```sql
-- 4. Verify the HNSW High-Performance Index is active
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'image_embeddings';

-- 5. Monitor Database Size (Relevant for 300k+ images)
SELECT pg_size_pretty(pg_total_relation_size('image_embeddings'));
```

### **Data Maintenance**
```sql
-- 6. Find potential duplicate entries (same object_key)
SELECT object_key, count(*) 
FROM image_embeddings 
GROUP BY object_key 
HAVING count(*) > 1;

-- 7. Delete an entry if a file was removed from S3
DELETE FROM image_embeddings WHERE object_key = 'path/to/removed_file.jpg';
```

---

## 💡 4. Useful PSQL Shortcuts
- `\dt`: List all tables.
- `\d image_embeddings`: View table columns and indexes.
- `\q`: Exit the database view.
- `\timing`: Toggle execution time (great for testing HNSW search speed).

---

## 🚀 5. Production Tips
- **Index Health**: PostgreSQL handles the HNSW index automatically, but if search feels slow after a massive 300k upload, you can run `REINDEX TABLE image_embeddings;`.
- **Backups**: To backup your indexed data:
  ```powershell
  docker exec vector_db pg_dump -U admin vectordb > backup_embeddings.sql
  ```
