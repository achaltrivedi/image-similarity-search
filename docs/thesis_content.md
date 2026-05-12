# Image Similarity Microservice: Thesis Content Breakdown

This document provides a highly structured, technical, and comprehensive breakdown of your thesis based on the "InHouse-Indexed Search" architecture, methodologies, and progress.

---

## 1. Introduction

### 1.1 Prologue
*   **Keywords:** Digital asset explosion, unstructured data, graphical asset management, enterprise storage, search paradigms.
*   **Content:** Begin by discussing the exponential growth of digital visual assets in modern enterprises (marketing, design, engineering). Highlight how massive data lakes or object storage buckets (like S3/MinIO) quickly become "data swamps" when assets cannot be efficiently discovered. Emphasize the shift from structured text data to unstructured multi-modal data.

### 1.2 Motivation
*   **Keywords:** Discoverability, workflow bottlenecks, manual tagging limitations, proprietary format opacity.
*   **Content:** Detail the pain points of creative and technical teams: spending countless hours searching for specific graphical assets (especially proprietary formats like Adobe Illustrator `.ai` or complex `.pdf` files) using inadequate, exact-match text searches. Discuss the frustration of lost assets, duplicate work, and the limitations of human-dependent metadata entry.

### 1.3 Objective
*   **Keywords:** Scalability, real-time ingestion, multi-modal vector search, sub-millisecond retrieval, microservices.
*   **Content:** To design, develop, and deploy a highly scalable, real-time image similarity search microservice capable of ingesting and indexing massive datasets (300k+ multi-format graphic assets). The system aims to enable sub-millisecond, multi-dimensional retrieval based on semantics, color, texture, and structural design without relying on manual metadata.

### 1.4 Problem Statement
*   **Keywords:** Semantic gap, legacy CBIR (Content-Based Image Retrieval), metadata dependency, synchronization latency.
*   **Content:** Traditional search systems rely on manual metadata tagging (which is error-prone, subjective, and non-scalable) or basic file-name matching. While standard semantic deep learning models exist, they often fail to capture low-level designer-focused metrics (exact color palettes, structural layout, texture). Furthermore, existing solutions struggle to maintain real-time, zero-latency synchronization between the core object storage layer and the vector search index when files are added, modified, or deleted.

### 1.5 Approach
*   **Keywords:** Event-driven architecture, multi-vector embeddings, HNSW indexing, CPU-optimized ONNX inference.
*   **Content:** Developed an event-driven microservices architecture. It utilizes MinIO for S3-compatible storage, triggering real-time background worker queues (Redis/RQ) upon file changes. A multi-modal embedding pipeline was engineered using ONNX-optimized CLIP models (for semantics) combined with computer vision algorithms (for color/texture/design). Data is stored and queried using PostgreSQL with the `pgvector` extension utilizing HNSW (Hierarchical Navigable Small World) indexing for Approximate Nearest Neighbor (ANN) search.

### 1.6 Scope and Project
*   **Keywords:** End-to-end pipeline, supported formats, UI/UX, out-of-scope boundaries.
*   **Content:** The scope encompasses the complete end-to-end pipeline: from raw asset upload to continuous ingestion, multi-vector processing, and frontend visualization via a modern React/Vite SPA using WebSockets for live updates. It explicitly covers complex formats (PNG, JPEG, PDF, AI, GIF, TIFF, BMP, WebP). Out of scope: generative image modification or text-to-image generation.

---

## 2. Literature Review (Previous Approaches)

*   **Keywords:** Folksonomy, SIFT/HOG, CNNs (ResNet/VGG), CLIP, multimodal alignment.
*   **Content Framework:**
    *   **Generation 1 (Manual/Text-based):** Keyword-based indexing, taxonomies, and manual tagging. Highly subjective and breaks down at scale.
    *   **Generation 2 (Traditional CBIR):** Utilizing algorithms like SIFT (Scale-Invariant Feature Transform) or HOG (Histogram of Oriented Gradients). Good for exact duplicate detection but zero semantic understanding (e.g., cannot understand that a "dog" and a "puppy" are related).
    *   **Generation 3 (Early Deep Learning):** Using Convolutional Neural Networks (CNNs) like ResNet or VGG to extract high-level feature maps. Better at general categorization, but lacked natural language alignment.
    *   **Generation 4 (Current State of the Art):** The introduction of CLIP (Contrastive Language-Image Pre-training) by OpenAI. Solved semantic understanding but typically lacks granular control over low-level visual traits (color, structure) when used in isolation. *Your project bridges this gap by combining CLIP with discrete visual vectors.*

---

## 3. Software Design & Methodology

*   **Keywords:** Microservices, Vector DB (`pgvector`), RQ/Redis, ONNX Runtime, Multi-modal extraction.
*   **Content Framework:**
    *   **System Architecture:** Describe the separated concerns: FastAPI backend, React frontend (ShadCN UI), PostgreSQL (pgvector) database, Redis job queue, and MinIO storage layer. Mention the Dockerized deployment strategy.
    *   **Real-Time Ingestion Pipeline:** Explain the event-driven nature. MinIO SDK `listen_bucket_notification()` streams `s3:ObjectCreated` events directly to the Redis Queue, ensuring the DB is never out of sync with the bucket.
    *   **Multi-Vector Embedding Pipeline (The Core Innovation):** Detail the 4 specific vectors generated per image:
        1.  *Semantic (`embedding`, 768D):* CLIP ViT-B/32 (ONNX CPU optimized).
        2.  *Structural (`design_embedding`, 256D):* Edge density grid using Canny edge detection.
        3.  *Color (`color_embedding`, 256D):* HSV Histogram (mean-centered).
        4.  *Texture (`texture_embedding`, 64D):* Grayscale Histogram.
    *   **Format Negotiation:** How the `ImagePreprocessor` handles proprietary formats like `.ai` and `.pdf`, rendering them to RGB in-memory before inference.
    *   **Data Retrieval:** Explain PostgreSQL's native `cosine_distance()` combined with HNSW indexes for sub-millisecond retrieval. Mention the WebSocket implementation for live UI updates.
    *   **Settings Page & Search Presets:** Discuss the dedicated Settings UI that allows users to adjust the weighting of the four vectors dynamically. Explain how predefined "Presets" (e.g., "Semantic Focus", "Color Match", "Strict Layout") interact with the backend API to alter the final distance calculation algorithm, giving the user unprecedented control over search behavior without needing code changes.

---

## 4. Results and Discussions

*   **Keywords:** Inference optimization, OOM prevention, vector querying speed, multi-dimensional accuracy.
*   **Content Framework:**
    *   **Performance Optimization:** Discuss the migration from pure PyTorch to ONNX Runtime. Detail how inference speed improved drastically (from >500ms down to ~100-200ms per image on CPU), and how removing the `torch` dependency shrunk the Docker image footprint.
    *   **Scalability & Stability:** Discuss the implementation of batched processing and threading Semaphores that prevented Out-Of-Memory (OOM) crashes during the massive ingestion of 300,000+ assets.
    *   **Search Granularity:** Discuss how the UI allows users to view the separated parameter-wise scores (semantics vs. color vs. texture). Explain how this multi-vector approach provides significantly higher precision for graphic designers than a pure CLIP semantic search.
    *   **UI/UX Latency & Customization:** Detail the success of WebSockets and the Redis-backed bucket cache for immediate visual feedback on deletions and uploads without heavy database locking. Highlight how the Settings page and Search Presets directly resolved user frustration by allowing them to instantly shift the search algorithm from a broad semantic query to a strict color or layout-based query depending on their immediate need.

---

## 5. Conclusion and Future Scope

*   **Keywords:** Production-readiness, multi-tenant SaaS, localized search.
*   **Content Framework:**
    *   **Conclusion:** Summarize the successful deployment of a robust, production-ready microservice that bridges the gap between raw object storage and intelligent, multi-dimensional graphic asset retrieval, successfully handling complex formats at scale.
    *   **Future Scope:**
        *   Implementing text-to-image semantic search (querying the database using text prompts via CLIP's text encoder).
        *   Transitioning to specialized cloud-native Vector DBs (e.g., Pinecone, Milvus or Qdrant) for multi-million scale if PostgreSQL limitations are reached.
        *   Implementing localized sub-image search (Object Detection/Bounding Box indexing) to find specific logos or assets *inside* larger composites.
        *   Expanding to a multi-tenant architecture for SaaS distribution.

---

## Diagram & Flowchart Generation Guide

To make your thesis visually impactful, you need high-quality architecture diagrams. 

### Recommended Tools
1.  **Draw.io / Diagrams.net (Best Overall):** Free, highly customizable, great for cloud/microservice architecture diagrams.
2.  **Mermaid.js (Best for Sequences):** Allows you to generate diagrams using code (text), which can be directly embedded in markdown files or Notion.
3.  **Lucidchart:** Excellent for professional, high-level system component interactions (requires subscription for complex diagrams).

### Prompts for Diagram Generation (Paste these into ChatGPT/Claude)

**Prompt 1: For the Overall System Architecture (Mermaid.js)**
> "Generate a Mermaid.js flowchart (graph TD) for an Image Similarity Search Microservice. It should show MinIO (S3) sending events to a Redis Queue. A Python Background Worker picks up jobs from Redis, processes images (extracting CLIP, Color, Texture, and Design vectors), and stores them in PostgreSQL (pgvector). The FastAPI backend serves a React/Vite Frontend and fetches presigned URLs from MinIO. Make it visually structured with subgraphs for 'Storage', 'Processing', 'Database', and 'Client'."

**Prompt 2: For the Multi-Vector Embedding Pipeline (Mermaid.js)**
> "Generate a Mermaid.js flowchart detailing an image embedding pipeline. The flow starts with a Raw Image (.png, .ai, .pdf). It goes into an 'Image Preprocessor'. From there, the flow splits into four parallel processing blocks: 1) ONNX CLIP Model (outputs 768D Semantic Vector), 2) Edge Density Extractor (outputs 256D Design Vector), 3) HSV Extractor (outputs 256D Color Vector), and 4) Grayscale Extractor (outputs 64D Texture Vector). All four vectors merge into a single 'PostgreSQL JSONB/Vector Row' block."

**Prompt 3: For the Real-Time Ingestion Sequence Diagram (Mermaid.js)**
> "Generate a Mermaid.js sequence diagram showing the real-time ingestion flow. The actors are: User, MinIO Storage, Worker Event Listener, Redis Queue, Worker Processor, and PostgreSQL. The user uploads a file to MinIO. MinIO triggers an s3:ObjectCreated event to the Event Listener. The listener pushes a job to Redis. The Worker Processor pulls the job, downloads the image from MinIO, computes embeddings, and inserts the data into PostgreSQL. Finally, the Worker Processor sends a WebSocket update to the User's UI."

---

## 6. Reference Tables

### 6.1 Multi-Vector Embedding Specifications
This table outlines the four distinct embedding models utilized during the ingestion pipeline to allow parameter-wise matching.

| Embedding Vector | Dimensions | Model / Method | Primary Purpose |
| :--- | :--- | :--- | :--- |
| **`embedding`** | 768D | CLIP ViT-B/32 (ONNX) | Semantic & conceptual similarity |
| **`design_embedding`** | 256D | Canny Edge Density Grid | Structural layout and composition |
| **`color_embedding`** | 256D | HSV Histogram (Mean-Centered)| Strict color palette matching |
| **`texture_embedding`** | 64D | Grayscale Histogram | Surface texture and granularity |

### 6.2 Microservices Architecture Services
This table details the discrete services running via Docker Compose in the production architecture.

| Service | Port | Description |
| :--- | :--- | :--- |
| **FastAPI Backend** | 8000 | Core Search API, webhook handler, and WebSocket broadcasting |
| **React Frontend** | 5173 (Dev) / 80 (Prod) | UI built with Vite, React, and ShadCN |
| **PostgreSQL** | 5434 | Primary database running the `pgvector` extension with HNSW indexes |
| **Redis** | 6379 | Job queuing system (RQ) and WebSocket Pub/Sub state manager |
| **MinIO API** | 9000 | S3-compatible object storage layer |
| **MinIO Console** | 9001 | MinIO Web Administration UI |

### 6.3 Supported Asset Formats
The system ingests and processes multiple graphic formats, negotiating them in-memory.

| Format | Processing Method | Feature Extraction Support |
| :--- | :--- | :--- |
| **.PNG / .JPEG / .WEBP** | Native RGB processing | Semantics, Color, Texture, Design |
| **.PDF** | First-page rendering at 300 DPI | Semantics, Color, Texture, Design |
| **.AI (Adobe Illustrator)** | PostScript/PDF extraction to raster | Semantics, Color, Texture, Design |
| **.GIF / .TIFF / .BMP** | Frame 1 extraction, format normalization | Semantics, Color, Texture, Design |

---

## 7. Abbreviations and Acronyms

*   **ANN**: Approximate Nearest Neighbor
*   **API**: Application Programming Interface
*   **CBIR**: Content-Based Image Retrieval
*   **CLIP**: Contrastive Language-Image Pre-training (OpenAI)
*   **CNN**: Convolutional Neural Network
*   **HNSW**: Hierarchical Navigable Small World (Vector Indexing Algorithm)
*   **HOG**: Histogram of Oriented Gradients
*   **HSV**: Hue, Saturation, Value (Color space)
*   **ONNX**: Open Neural Network Exchange
*   **OOM**: Out of Memory
*   **RQ**: Redis Queue
*   **S3**: Simple Storage Service (AWS standard, utilized via MinIO)
*   **SDK**: Software Development Kit
*   **SIFT**: Scale-Invariant Feature Transform
*   **SPA**: Single Page Application
*   **TTL**: Time To Live
*   **UI/UX**: User Interface / User Experience
