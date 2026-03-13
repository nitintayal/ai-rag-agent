# ai-rag-agent

🧠 **Agentic AI RAG System — Local, Offline & Dockerized**

An **Agentic Retrieval-Augmented Generation (RAG)** system built using **Python, FAISS, Sentence Transformers, LangGraph, FastAPI, and Docker**.

This project enables intelligent question answering over your own documents using a **local AI agent workflow**, persistent vector storage, offline inference, and containerized deployment.

---

# 🤖 Agentic Local RAG System

Unlike traditional RAG pipelines, this system introduces an **AI Agent layer** powered by **LangGraph**, enabling structured reasoning and tool execution.

The agent dynamically executes workflow steps such as:

✅ Retrieve knowledge
✅ Process context
✅ Generate grounded responses

All running **fully locally**.

No external LLM APIs required after initial model download.

---

## 🚀 Features

* 📄 Document ingestion from local `.txt`, `.xlsx` and `.pdf` files
* ✂️ Intelligent document chunking
* 🧠 Semantic embeddings using Sentence Transformers
* 📦 FAISS vector similarity search
* 💾 Persistent disk-backed vector database
* 🔄 Incremental ingestion (only new documents embedded)
* 🤖 **LangGraph Agent Workflow**
* 🧰 RAG converted into Agent Tool
* 🌐 FastAPI REST API
* 📚 Source-aware grounded answers
* 📊 Confidence scoring
* 🐳 Docker & Docker Compose deployment
* 🔐 Fully offline inference support

---

## 🧠 Agent Architecture Overview

```
User Question
      ↓
FastAPI API
      ↓
Agent Executor
      ↓
LangGraph Agent
      ↓
RAG Tool (Knowledge Retrieval)
      ↓
FAISS Vector Store
      ↓
Local LLM
      ↓
Answer + Sources + Confidence
```

---

## ⚙️ Agent Workflow (LangGraph)

The AI agent executes a structured workflow:

```
retrieve → generate → END
```

### Agent Nodes

| Node     | Responsibility           |
| -------- | ------------------------ |
| Retrieve | Searches knowledge base  |
| Generate | Produces grounded answer |
| End      | Returns final response   |

This enables extensibility toward multi-tool autonomous agents.

---

## 🛠 Tech Stack

* **Python 3.11+**
* **LangGraph**
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
│   ├── __init__.py
│   ├── rag_tool.py
│   ├── agent_graph.py
│   ├── agent_executor.py
│   └── local_llm_answer.py
│
├── embeddings/
├── ingestion/
├── retrieval/
│
├── data/
├── storage/
│   ├── faiss.index
│   └── documents.pkl
│
├── main.py
├── api.py
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

## 3️⃣ Build Vector Index

```bash
python main.py
```

Processes documents and builds FAISS index.

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

## Build Image

```bash
docker build -t ai-rag-agent .
```

---

## Run Container

```bash
docker run --rm \
-p 8000:8000 \
-v $(pwd)/storage:/app/storage \
-v ~/.cache/huggingface:/root/.cache/huggingface \
ai-rag-agent
```

---

## ✅ Persistent Volumes

| Volume     | Purpose             |
| ---------- | ------------------- |
| storage    | FAISS persistence   |
| HF cache   | Offline models      |
| Host mount | Stateless container |

---

# 🐳 Docker Compose (Recommended)

Start:

```bash
docker compose up
```

Background:

```bash
docker compose up -d
```

Stop:

```bash
docker compose down
```

---

# 🔐 Offline Mode

After first download:

```
HF_HUB_OFFLINE=1
```

Mounted cache:

```
~/.cache/huggingface → container
```

No runtime internet dependency.

---

## 📄 Supported Documents

* `.txt`
* `.xlsx`
* `.pdf` ✨ **NEW**

Add files to:

```
data/
```

Re-run ingestion:

```bash
python main.py
```

---

## 🌐 API Usage

### Endpoint

```
POST /ask
```

### Request

```json
{
  "question": "What employee data exists?"
}
```

### Response

```json
{
  "answer": "...",
  "confidence": 0.87,
  "sources": ["employee.xlsx"]
}
```

---

## 🧠 Design Principles

* Stateless containers
* Persistent vector storage
* Tool-based agent architecture
* Offline-first AI deployment
* Reproducible environments

---

## 💼 Skills Demonstrated

* Agentic RAG Architecture
* LangGraph Workflow Design
* Tool-based AI Systems
* Vector Databases (FAISS)
* FastAPI Backend Engineering
* Dockerized AI Deployment
* Offline LLM Inference
* Production-ready AI Infrastructure

---

## 🚀 Future Enhancements

* ReAct decision agent
* Multi-tool routing
* Conversation memory
* Redis caching
* Streaming responses
* Kubernetes deployment

---

## 📜 License

MIT
