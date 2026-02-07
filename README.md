# ai-rag-agent
Agentic RAG system using LLMs and LangGraph

# 🔎 Local RAG Agent (Sentence Transformers + FAISS + Local LLM)

A fully local Retrieval-Augmented Generation (RAG) system that answers questions using your own documents, with **source citations** and **confidence scoring** — no external LLM APIs required.

---

## 🚀 Features

- 📄 Document ingestion from local files
- ✂️ Intelligent text chunking
- 🧠 Semantic embeddings using Sentence Transformers
- 📦 Vector search with FAISS
- 💾 Persistent vector database (disk-backed)
- 🤖 Local LLM answering (CPU-safe)
- 📚 Source citations for every answer
- 📊 Confidence score based on similarity

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
- **Local LLM** – Qwen2 / MiniCPM (CPU-safe)
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
├── data/
│ └── *.txt
├── storage/
│ ├── faiss.index
│ └── documents.pkl
├── main.py
├── requirements.txt
└── README.md


---

## ▶️ How to Run

### 1️⃣ Create & activate virtual environment

```bash
python -m venv venv
source venv/bin/activate
