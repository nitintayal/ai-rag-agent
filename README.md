# ai-rag-agent
Agentic RAG system using LLMs, FAISS, and FastAPI

# 🔎 Local RAG Agent (Sentence Transformers + FAISS + Local LLM)

A fully local Retrieval-Augmented Generation (RAG) system that answers questions using your own documents, with **source citations** and **confidence scoring** — no external LLM APIs required after initial model download.

---

## 🚀 Features

- 📄 Document ingestion from local `.txt` and `.xlsx` files
- ✂️ Intelligent text chunking
- 🧠 Semantic embeddings using Sentence Transformers
- 📦 Vector search with FAISS
- 💾 Persistent vector database (disk-backed)
- 🔄 Incremental ingestion (only new documents are embedded)
- 🤖 Local LLM answering (CPU-safe)
- 🌐 REST API using FastAPI
- 📚 Source citations for every answer
- 📊 Confidence score based on similarity
- 🔐 Fully offline mode supported

---

## 🧠 Architecture Overview

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



---

## 🛠 Tech Stack

- **Python 3.11+**
- **Sentence Transformers** – semantic embeddings
- **FAISS** – vector database & similarity search
- **Transformers (Hugging Face)** – local LLM inference
- **FastAPI** – API layer
- **NumPy / Torch**

---

## 📂 Project Structure

ai-rag-agent/
├── agent/
│ └── local_llm_answer.py
├── embeddings/
│ └── sentence_embeddings.py
├── ingestion/
│ ├── load_documents.py
│ └── chunk_documents.py
├── retrieval/
│ └── vector_store.py
├── data/ # Input documents (.txt, .xlsx)
├── storage/ # FAISS index + metadata
│ ├── faiss.index
│ └── documents.pkl
├── main.py # CLI-based RAG
├── api.py # FastAPI service
├── requirements.txt
└── README.md


## ▶️ How to Run (CLI Mode)

### 1️⃣ Create & activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate

2️⃣ Install dependencies
pip install -r requirements.txt

3️⃣ Build Vector Index (Ingestion)
python main.py
