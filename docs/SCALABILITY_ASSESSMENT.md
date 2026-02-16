# Scalability Assessment: 1.6TB Data / 300,000 Images

This document evaluates the capability of the current architecture to handle your company's production volume of **1.6TB** and **300,000+ images**.

---

## 💾 1. Storage Analysis

### **Original Data (OMS S3 Bucket)**
- **Size**: 1.6 TB
- **Status**: **Capable.** 
- **Why?**: Our system **does not store original images**. It only stores a reference (the `object_key`). S3 is designed to handle Petabytes of data; 1.6TB is well within its sweet spot.

### **Database (PostgreSQL + pgvector)**
- **Vector Size**: 768 dimensions (float32).
- **Data per Record**: ~3.1 KB per image (including vector, metadata, and overhead).
- **300,000 Records**: ~0.9 GB of raw vector data.
- **HNSW Index Overhead**: ~3 GB.
- **Estimated Total DB Size**: **< 5 GB**.
- **Status**: **Extremely Capable.** 
- **Why?**: A 5GB database is considered "small" for modern PostgreSQL. It can easily stay resident in RAM for maximum speed.

---

## ⚡ 2. Search Performance (The HNSW Advantage)

At 300,000 images, a standard "linear scan" (finding similarity by comparing every single row) would take roughly **200-500ms**, which is too slow for a real-time OMS.

- **Current Design**: We have implemented an **HNSW (Hierarchical Navigable Small World)** index.
- **Performance Expectation**: Even with 3lac images, search time will be **< 50ms**.
- **Scalability**: HNSW scales logarithmically. You could grow to **10 Million images**, and the search speed would still likely stay under 100ms.

---

## 🏎️ 3. Ingestion Bottleneck (The Batch Phase)

The primary challenge isn't storing or searching—it's the **initial ingestion**.

- **Batch Size**: 3lac images.
- **Compute**: Generating a CLIP embedding takes ~20ms on a GPU or ~200-500ms on a CPU.
- **Network**: 1.6TB of data must be streamed from S3 to your embedding service.
- **Strategy**: Our `tools/batch_indexer.py` is designed for this. It uses **pagination** and **idempotency** to ensure the 1.6TB process can be paused, resumed, and managed in chunks without crashing.

---

## 🖥️ 4. Hardware Recommendations for 1.6TB Scale

To handle this volume smoothly in production, we recommend:

| Component | Minimum | Recommended (OMS Prod) |
| :--- | :--- | :--- |
| **Postgres RAM** | 4 GB | 16 GB (Enough to keep the 5GB index in memory) |
| **Embedding CPU/GPU**| 4-8 vCPUs| **NVIDIA GPU (e.g., T4 or A10)** for 10x faster batching |
| **Storage (DB)** | 20 GB SSD | 100 GB SSD (NVMe for faster indexing) |

---

## 🎯 Verdict
**YES, the design is 100% capable.**

The separation of **Storage (S3)**, **Search (HNSW/Postgres)**, and **Automation (Webhooks)** is the exact architecture used by major enterprises to handle millions of assets. 

The **1.6TB** is handled by S3's massive scale, and the **300k images** are handled by HNSW's efficient geometry. Your biggest task will simply be the initial ingestion time (which we have the tools for).
