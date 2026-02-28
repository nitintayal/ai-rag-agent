# ai-rag-agent

🧠 Agentic AI RAG system — Local, Offline & Dockerized

An Agentic Retrieval-Augmented Generation (RAG) system built using Python, FAISS, Sentence Transformers, FastAPI, and Docker.

This project enables question answering over your own documents using a fully local LLM pipeline, with persistent vector storage, offline inference, and containerized deployment.

---

# 🔎 Local RAG Agent (Sentence Transformers + FAISS + Local LLM)

A fully local **Retrieval-Augmented Generation (RAG)** system that answers questions using your own documents with:

✅ Source citations
✅ Confidence scoring
✅ Persistent vector storage
✅ FastAPI API
✅ Dockerized deployment
✅ Fully Offline Inference

No external LLM APIs required after initial model download.

---

## 🚀 Features

* 📄 Document ingestion from local `.txt` and `.xlsx` files
* ✂️ Intelligent text chunking
* 🧠 Semantic embeddings using Sentence Transformers
* 📦 Vector similarity search using FAISS
* 💾 Persistent disk-backed vector database
* 🔄 Incremental ingestion (only new documents embedded)
* 🤖 Local LLM answering (CPU-safe)
* 🌐 REST API using FastAPI
* 📚 Source citations for answers
* 📊 Confidence scoring
* 🐳 Docker & Docker Compose support
* 🔐 Fully offline execution supported

---

## 🧠 Architecture Overview

```
Documents
   ↓
Chunking
   ↓
Sentence Transformers (Embeddings)
   ↓
FAISS Vector Store (Persisted)
   ↓
Semantic Retrieval (Top-K)
   ↓
Local LLM (Answer Generation)
   ↓
Answer + Confidence + Sources
```

---

## 🛠 Tech Stack

* **Python 3.11+**
* **Sentence Transformers**
* **FAISS**
* **HuggingFace Transformers**
* **FastAPI**
* **Torch / NumPy**
* **Docker**
* **Docker Compose**

---

## 📂 Project Structure

```
ai-rag-agent/
├── agent/
│   └── local_llm_answer.py
├── embeddings/
│   └── sentence_embeddings.py
├── ingestion/
│   ├── load_documents.py
│   └── chunk_documents.py
├── retrieval/
│   └── vector_store.py
├── data/                # Input documents
├── storage/             # FAISS index persistence
│   ├── faiss.index
│   └── documents.pkl
├── main.py              # CLI ingestion
├── api.py               # FastAPI service
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

# ▶️ Local Execution (CLI Mode)

## 1️⃣ Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 3️⃣ Build Vector Index (Ingestion)

```bash
python main.py
```

This step:

* Loads documents from `/data`
* Splits text into chunks
* Generates embeddings
* Stores vectors in `/storage`

---

## 4️⃣ Run FastAPI Server

```bash
uvicorn api:app --reload --port 8000
```

Open:

```
http://localhost:8000/docs
```

---

# 🐳 Docker Setup

## Install Docker Desktop

Download:

[https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)

Verify:

```bash
docker --version
```

---

## Build Docker Image

From project root:

```bash
docker build -t ai-rag-agent .
```

---

## Run Container (Recommended)

```bash
docker run --rm \
-p 8000:8000 \
-v $(pwd)/storage:/app/storage \
-v ~/.cache/huggingface:/root/.cache/huggingface \
ai-rag-agent
```

---

## ✅ Why Volumes Are Mounted

| Volume            | Purpose                       |
| ----------------- | ----------------------------- |
| `storage/`        | Persist FAISS vector database |
| HuggingFace cache | Prevent model re-download     |
| Host filesystem   | Container remains stateless   |

Containers can be recreated safely without data loss.

---

# 🐳 Docker Compose (Recommended)

Start system:

```bash
docker compose up
```

Run in background:

```bash
docker compose up -d
```

Stop:

```bash
docker compose down
```

Compose automatically:

✅ Builds image
✅ Mounts persistent storage
✅ Mounts HuggingFace cache
✅ Enables offline inference

---

## docker-compose.yml Highlights

* API container orchestration
* Persistent vector DB
* Shared model cache
* Restart resilience

---

# 🔐 Offline Mode

After first model download, system runs fully offline.

Environment variable used:

```
HF_HUB_OFFLINE=1
```

Mounted cache:

```
~/.cache/huggingface → container cache
```

Prevents internet downloads during runtime.

---

## 📄 Supported Documents

* `.txt`
* `.xlsx` (row-wise embedding)

Add files into:

```
data/
```

Then rerun:

```bash
python main.py
```

Only new documents are embedded.

---

## 🔄 Incremental Ingestion

* Existing vectors preserved
* Only new files processed
* Faster updates for growing datasets

---

## 🌐 API Usage

### Endpoint

```
POST /ask
```

### Request

```json
{
  "question": "What is leave policy?"
}
```

### Response

```json
{
  "answer": "...",
  "sources": ["employee.xlsx"],
  "confidence": 0.87
}
```

---

## 🧠 Key Design Principles

* Containers are **stateless**
* Persistent data stored outside containers
* Models cached once and reused
* Offline-first ML inference
* Reproducible deployments

---

## 💼 Skills Demonstrated

* Retrieval-Augmented Generation (RAG)
* Vector database implementation
* Incremental ingestion pipelines
* FastAPI backend engineering
* Docker containerization
* Volume persistence strategy
* Offline ML deployment
* Production-ready AI architecture

---

## 🚀 Future Enhancements

* Redis caching
* Hybrid search (BM25 + Vector)
* Streaming responses
* Async ingestion workers
* Dedicated model service
* Kubernetes deployment

---

## 📜 License

MIT
