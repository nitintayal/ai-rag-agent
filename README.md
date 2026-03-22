# 🧠 AI RAG Agent (Agentic + Hybrid Search + Re-Ranking)

🚀 **Production-grade Agentic Retrieval-Augmented Generation (RAG) system** with:

* 🤖 LangGraph-powered agent workflow
* 🔍 Hybrid search (FAISS + BM25)
* 🧠 Cross-encoder re-ranking (MS MARCO)
* ⚡ Streaming responses (ChatGPT-style UI ready)
* 📦 Fully Dockerized & Offline-capable

---

# ✨ What Makes This Special

This is **not just a RAG system** — it is an **Agentic AI system** where:

* RAG is implemented as a **tool**
* A **LangGraph agent** decides how to use it
* Retrieval is enhanced with **Hybrid Search + Re-ranking**

👉 This mirrors **real-world production AI systems** (Perplexity, OpenAI Retrieval, enterprise RAG).

---

# 🚀 Features

## 🧠 Retrieval Intelligence

* ✅ Semantic Search (FAISS)
* ✅ Keyword Search (BM25)
* ✅ **Hybrid Search (Vector + Keyword)**
* ✅ **Cross-Encoder Re-ranking (MS MARCO)**
* ✅ Top-K context filtering
* ✅ Token-based chunking (with overlap)

---

## 🤖 Agent Capabilities

* LangGraph-based workflow
* RAG exposed as tool
* Extensible multi-tool architecture
* Deterministic reasoning flow

---

## 📄 Document Handling

* `.txt`, `.xlsx`, `.pdf`
* Incremental ingestion (only new docs)
* Delete documents from knowledge base
* Persistent FAISS index

---

## 🌐 API Layer

* FastAPI backend
* Streaming responses (`/ask`)
* File upload (`/upload`)
* Delete endpoint (`/delete`)
* CORS-enabled

---

## 💻 Frontend Ready

* ChatGPT-style streaming UI
* Typing indicator support
* Source attribution
* Real-time updates

---

## 🐳 DevOps & Deployment

* Docker + Docker Compose
* Persistent vector storage
* HuggingFace cache mounting
* Offline inference ready

---

# 🧠 Architecture Overview

```id="arch1"
User Query
   ↓
FastAPI API
   ↓
LangGraph Agent
   ↓
RAG Tool
   ↓
Hybrid Retrieval
   (FAISS + BM25)
   ↓
Cross-Encoder Re-ranking
   ↓
Top-K Context
   ↓
Local LLM
   ↓
Streaming Answer + Sources
```

---

# ⚙️ Agent Workflow

```id="workflow1"
retrieve → rerank → generate → END
```

| Node     | Description                   |
| -------- | ----------------------------- |
| Retrieve | Hybrid search (vector + BM25) |
| Rerank   | Cross-encoder scoring         |
| Generate | LLM grounded response         |
| End      | Final output                  |

---

# 📂 Project Structure

```id="structure1"
ai-rag-agent/
│
├── agent/
│   ├── rag_tool.py
│   ├── agent_graph.py
│   ├── agent_executor.py
│   └── local_llm_answer.py
│
├── ingestion/
│   ├── load_documents.py
│   ├── chunk_documents.py
│   └── ingest_documents.py
│
├── embeddings/
├── retrieval/
│   └── vector_store.py
│
├── reranker/
│   └── cross_encoder.py
│
├── data/
├── storage/
│   ├── faiss.index
│   └── documents.pkl
│
├── api.py
├── main.py
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

# ▶️ Local Setup

## 1️⃣ Create environment

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 2️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

---

## 3️⃣ Ingest documents

```bash
python main.py
```

---

## 4️⃣ Run API

```bash
uvicorn api:app --reload --port 8000
```

---

## 5️⃣ Open Swagger

```
http://localhost:8000/docs
```

---

# 🐳 Docker Setup

```bash
docker compose up --build
```

---

# 🔐 Offline Mode

After first model download:

```bash
export HF_HUB_OFFLINE=1
```

Cache mounted from:

```
~/.cache/huggingface
```

---

# 🌐 API Usage

## POST `/ask`

```json
{
  "question": "What is leave policy?"
}
```

### Streaming Response

```
Answer text...

Sources:
- employee_policy.pdf
- leave_rules.xlsx
```

---

## POST `/upload`

Upload document via form-data.

---

## DELETE `/delete`

```
/delete?source=employee.xlsx
```

---

# ⚡ Key Innovations

* Hybrid Retrieval (FAISS + BM25)
* Cross-Encoder Re-ranking
* Token-based chunking with overlap
* Streaming LLM responses
* Agent-based orchestration
* Incremental indexing pipeline

---

# 📈 Why Hybrid + Re-ranking Matters

| Approach     | Result                     |
| ------------ | -------------------------- |
| Vector only  | misses keywords ❌          |
| BM25 only    | misses semantics ❌         |
| Hybrid       | balanced retrieval ✅       |
| + Re-ranking | highly accurate context 🚀 |

---

# 🧠 Design Principles

* Stateless containers
* Persistent knowledge store
* Agent-driven orchestration
* Offline-first ML deployment
* Modular architecture

---

# 💼 Skills Demonstrated

* Agentic AI Systems (LangGraph)
* Retrieval-Augmented Generation (RAG)
* Hybrid Search (Vector + BM25)
* Re-ranking (Cross-Encoder Models)
* FastAPI + Streaming APIs
* React-ready real-time UI
* Dockerized AI deployment
* Offline AI inference

---

# 🚀 Future Enhancements

* ReAct-style decision agents
* Multi-tool agent routing
* Conversation memory
* Redis caching
* Perplexity-style citations (highlight chunks)
* Kubernetes deployment

---

# 📜 License

MIT


## Next

* Confidence Score In API response
* Tool routing (LangGraph strength) User query -> Decision node -> RAG / Tool / LLM
* Show uploaded documents in UI
* ReIndex Button (Upload → Index manually)
* Performance & Scaling (Redis / in-memory cache) [question → answer]
* Background ingestion (upload → queue → worker → index)
* Environmental Configs (.env, MODEL_NAME=, TOP_K= ,CHUNK_SIZE= )
* Upload from UI → instant query Already close — just polish UX.
* Multi-user support (session id, chat id)
* Multi-tool agent with LangGraph

