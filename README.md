# AI Personal Assistant

A full-stack AI personal assistant powered by local LLMs (Ollama), with RAG document search, web search, journal, task management, persistent memory, and calendar — all running privately on your machine. No cloud API keys required.

## Features

- **Chat with real-time streaming** — token-by-token responses via Server-Sent Events (SSE)
- **RAG document search** — upload PDFs, TXT, XLSX, CSV and ask questions with hybrid retrieval (FAISS vector search + BM25 keyword search + cross-encoder reranking)
- **Web search** — routes time-sensitive queries to DuckDuckGo with parallel page content extraction via trafilatura
- **Task management** — create, complete, filter, and track tasks with priorities (low/medium/high) and due dates
- **Journal** — personal journal with full CRUD, mood tagging, and semantic search powered by sentence embeddings
- **Persistent memory** — remembers user preferences and facts across conversations using embedding-based recall
- **Calendar** — simple event management with date/time tracking
- **Conversation history** — multi-turn context within sessions, stored in SQLite
- **Intelligent tool routing** — LLM-powered router with keyword fallback automatically selects the right tool per query
- **Memory extraction** — optionally extracts and stores personal facts from conversations for future context

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Frontend: React + Tailwind CSS + Vite                   │
│  Chat (SSE) │ Tasks Panel │ Journal Panel │ File Upload   │
└─────────────────────────┬────────────────────────────────┘
                          │ HTTP / SSE
┌─────────────────────────▼────────────────────────────────┐
│  API Layer (FastAPI)                                     │
│  POST /chat  │ /tasks  │ /journal  │ /upload  │ /health  │
└─────────────────────────┬────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────┐
│  Agent Layer (LangGraph StateGraph)                      │
│  route → execute_tool → generate → extract_memory        │
└────────┬────────────┬────────────┬───────────────────────┘
         │            │            │
    ┌────▼────┐  ┌────▼────┐  ┌───▼─────┐
    │  LLM    │  │  Tools  │  │  Memory │
    │ (Ollama)│  │  (6)    │  │         │
    └─────────┘  └────┬────┘  └───┬─────┘
                      │           │
               ┌──────▼──────┐ ┌──▼────────┐
               │  Retrieval  │ │  Storage   │
               │ FAISS+BM25  │ │  SQLite    │
               └─────────────┘ └────────────┘
```

### Layered Architecture

The codebase is organized into 7 independent layers with strict top-down dependencies (no circular imports):

```
API Layer  →  Agent Layer  →  LLM Layer
                            →  Tool Layer  →  Retrieval Layer
                                           →  Storage Layer
                            →  Memory Layer →  Storage Layer
```

| Layer | Purpose | Key Files |
|-------|---------|-----------|
| **API** | FastAPI endpoints, SSE streaming, request/response schemas | `api/app.py`, `api/routes/`, `api/schemas/` |
| **Agent** | LangGraph state graph, tool orchestration, sync + streaming runners | `agent/graph.py`, `agent/nodes.py`, `agent/runner.py` |
| **LLM** | Ollama REST client (sync, async, streaming), prompt templates, model management | `llm/ollama_client.py`, `llm/prompts.py`, `llm/model_manager.py` |
| **Tools** | 6 independent tools with uniform `BaseTool` interface and registry | `tools/base.py`, `tools/registry.py`, `tools/*.py` |
| **Memory** | Conversation history (per-session), long-term user facts (cross-session), context builder | `memory/conversation_memory.py`, `memory/long_term_memory.py`, `memory/context_builder.py` |
| **Retrieval** | FAISS vector index, BM25 keyword index, hybrid search, cross-encoder reranking, document ingestion | `retrieval/`, `embeddings/`, `ranker/`, `ingestion/` |
| **Storage** | SQLite database, schema management, repository pattern for all entities | `storage/database.py`, `storage/repositories/` |

### Tools

| Tool | Description | Backing |
|------|-------------|---------|
| `rag` | Hybrid search over uploaded documents with reranking | FAISS + BM25 + cross-encoder |
| `web` | DuckDuckGo search with parallel page content extraction | ddgs + trafilatura |
| `journal` | Journal entries — create, search, list | SQLite + sentence embeddings |
| `task` | Task/reminder management with status, priority, due dates | SQLite |
| `memory` | Store and recall user preferences and facts | SQLite + sentence embeddings |
| `calendar` | Calendar event management | SQLite |

### Agent Flow

The LangGraph agent processes each query through this graph:

```
1. ROUTE      → LLM decides which tool to use (with keyword fallback)
                 "rag" | "web" | "journal" | "task" | "memory" | "calendar" | "direct"

2. EXECUTE    → Selected tool runs and returns context + sources
                 (skipped for "direct" — simple questions answered without tools)

3. GENERATE   → LLM produces the answer using:
                 - Tool context (search results, task list, etc.)
                 - Conversation history (last 20 messages)
                 - User memory (known preferences and facts)

4. EXTRACT    → (Optional) LLM extracts memorable facts from the exchange
                 e.g., "user prefers Python" → stored for future conversations
```

### How Memory Works

**Short-term (conversation memory):**
- Every message (user + assistant) is stored in SQLite per `conversation_id`
- On each turn, the last 20 messages are loaded as context for the LLM
- The frontend generates a `conversation_id` per chat session

**Long-term (user memory):**
- Personal facts are extracted from conversations via an LLM call (configurable)
- Facts are stored as key-value pairs with sentence embeddings
- On each turn, relevant facts are recalled via semantic search and injected into the system prompt
- Example: user says "I'm a data scientist" → stored → future responses are tailored accordingly

### Retrieval Pipeline

When the `rag` tool is selected:

```
Query
  ↓
Embed query (sentence-transformers/all-MiniLM-L6-v2)
  ↓
Hybrid search:
  ├── FAISS vector search (cosine similarity, weight: 0.7)
  ├── BM25 keyword search (weight: 0.3)
  └── Merge + normalize scores
  ↓
Filter by MIN_HYBRID_SCORE (0.15)
  ↓
Cross-encoder reranking (ms-marco-MiniLM-L-6-v2)
  ↓
Filter by MIN_RERANK_SCORE (0.10)
  ↓
Top-K documents → formatted context for LLM
```

Document ingestion: files are loaded (PDF/TXT/XLSX/CSV) → chunked by token count (400 tokens, 80 overlap via tiktoken) → embedded → stored in FAISS index.

## Project Structure

```
ai-rag-agent/
├── api/                          # API Layer
│   ├── app.py                    #   FastAPI app, CORS, lifespan
│   ├── routes/
│   │   ├── chat.py               #   POST /chat (SSE), POST /chat/sync
│   │   ├── documents.py          #   POST /upload, DELETE /delete
│   │   ├── journal.py            #   /journal/* CRUD + search
│   │   ├── tasks.py              #   /tasks/* CRUD
│   │   └── health.py             #   GET /health, /status
│   └── schemas/
│       ├── chat.py               #   ChatRequest, ChatResponse
│       └── tasks.py              #   TaskCreate, TaskUpdate
│
├── agent/                        # Agent Layer
│   ├── graph.py                  #   LangGraph StateGraph definition
│   ├── state.py                  #   AgentState TypedDict
│   ├── nodes.py                  #   Graph nodes: route, execute_tool, generate, extract_memory
│   └── runner.py                 #   run_agent() sync + run_agent_stream() async
│
├── llm/                          # LLM Layer
│   ├── ollama_client.py          #   OllamaClient: chat, generate, chat_stream
│   ├── prompts.py                #   System, router, answer, memory extraction prompts
│   └── model_manager.py          #   Check/list/pull Ollama models
│
├── tools/                        # Tool Layer
│   ├── base.py                   #   BaseTool ABC, ToolResult, ToolDefinition
│   ├── registry.py               #   Tool registry: get_all_tools(), get_tool()
│   ├── rag_tool.py               #   RAG hybrid search tool
│   ├── web_tool.py               #   Web search tool
│   ├── journal_tool.py           #   Journal CRUD + search tool
│   ├── task_tool.py              #   Task management tool
│   ├── memory_tool.py            #   User memory store/recall tool
│   └── calendar_tool.py          #   Calendar event tool
│
├── memory/                       # Memory Layer
│   ├── conversation_memory.py    #   Per-session message history
│   ├── long_term_memory.py       #   Cross-session user facts with semantic recall
│   └── context_builder.py        #   Builds LLM message list from all context sources
│
├── retrieval/                    # Retrieval Layer
│   └── vector_store.py           #   FAISS + BM25 hybrid search
│
├── embeddings/
│   └── sentence_embeddings.py    #   SentenceTransformer wrapper
│
├── ranker/
│   └── cross_encoder.py          #   Cross-encoder reranking
│
├── ingestion/                    # Document Ingestion
│   ├── load_documents.py         #   PDF, TXT, XLSX, CSV loaders
│   ├── chunk_documents.py        #   Token-based chunking (tiktoken)
│   └── ingest_documents.py       #   Orchestration: load → chunk → embed → store
│
├── storage/                      # Storage Layer
│   ├── database.py               #   SQLite setup, schema, connection manager
│   └── repositories/
│       ├── user_repo.py          #   User profiles
│       ├── conversation_repo.py  #   Conversations + messages
│       ├── journal_repo.py       #   Journal entries
│       ├── task_repo.py          #   Tasks
│       └── memory_repo.py        #   User memories
│
├── mcp_servers/                  # MCP Tool Servers (stdio)
│   ├── servers.json              #   Server config
│   ├── client/
│   │   └── mcp_client.py         #   MCP stdio client
│   └── servers/
│       ├── rag_server.py         #   search_documents() MCP server
│       ├── web_server.py         #   search_web() MCP server
│       └── journal_server.py     #   Journal CRUD MCP server
│
├── configs/
│   └── config.py                 #   Pydantic BaseSettings (.env loader)
│
├── data/                         #   (gitignored) runtime data
│   ├── files/                    #   Uploaded documents
│   ├── storage/                  #   FAISS index + pickled documents
│   └── db/                       #   SQLite databases
│
├── .env.example                  #   Configuration template
├── requirements.txt              #   Python dependencies
├── Dockerfile                    #   Container build
└── docker-compose.yml            #   Docker Compose setup
```

## Getting Started

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com/download) installed and running
- Node.js 18+ (for the frontend)

### 1. Install Ollama

Download from [ollama.com/download](https://ollama.com/download), install, and launch it. Then pull the model:

```bash
ollama pull qwen2.5:7b
```

This downloads ~4.7 GB. Requires ~8 GB free RAM to run.

### 2. Backend Setup

```bash
cd ai-rag-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env

# Start the server
python -m api.app
```

The API runs at `http://localhost:8000`.
- `http://localhost:8000/health` — health check
- `http://localhost:8000/status` — system status (Ollama connectivity, models, features)
- `http://localhost:8000/docs` — interactive API docs (Swagger)

### 3. Frontend Setup

```bash
cd ai-rag-ui

npm install
npm run dev
```

Opens at `http://localhost:5173`.

## Configuration Reference

All settings are in `.env` (loaded via Pydantic BaseSettings):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_CHAT_MODEL` | `qwen2.5:7b` | Model for chat and routing |
| `OLLAMA_TIMEOUT` | `120` | Request timeout in seconds |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model for retrieval + memory |
| `RERANK_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder for reranking |
| `VECTOR_WEIGHT` | `0.7` | Weight for vector search in hybrid |
| `BM25_WEIGHT` | `0.3` | Weight for BM25 in hybrid |
| `HYBRID_K` | `10` | Number of candidates from hybrid search |
| `RERANK_K` | `5` | Number of documents after reranking |
| `MIN_HYBRID_SCORE` | `0.15` | Minimum score to pass hybrid search |
| `MIN_RERANK_SCORE` | `0.10` | Minimum score to pass reranking |
| `CHUNK_SIZE` | `400` | Token count per chunk |
| `CHUNK_OVERLAP` | `80` | Overlap between chunks in tokens |
| `WEB_SEARCH_MAX_RESULTS` | `3` | Max DuckDuckGo results per query |
| `API_PORT` | `8000` | FastAPI server port |
| `DATABASE_PATH` | `data/db/assistant.db` | SQLite database path |
| `DATA_DIR` | `data/files` | Uploaded document storage |
| `STORAGE_DIR` | `data/storage` | FAISS index storage |
| `CONVERSATION_HISTORY_LIMIT` | `20` | Messages loaded per conversation turn |
| `MEMORY_EXTRACTION_ENABLED` | `true` | Extract user facts from conversations |
| `DEBUG` | `false` | Enable debug mode with auto-reload |

## API Endpoints

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Chat with SSE streaming. Body: `{question, user_id?, conversation_id?}` |
| POST | `/chat/sync` | Chat without streaming. Returns `{answer, sources, tool}` |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload` | Upload a document (PDF, TXT, XLSX, CSV). Multipart form with `file` field |
| DELETE | `/delete?source=filename` | Remove a document from the index |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tasks?user_id=&status=` | List tasks, optionally filtered by status |
| POST | `/tasks?user_id=` | Create a task. Body: `{title, description?, due_date?, priority?}` |
| GET | `/tasks/{id}?user_id=` | Get a single task |
| PATCH | `/tasks/{id}?user_id=` | Update a task. Body: `{title?, status?, priority?, due_date?}` |
| DELETE | `/tasks/{id}?user_id=` | Delete a task |

### Journal

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/journal/entries?user_id=&limit=&offset=` | List entries with pagination |
| POST | `/journal/entries` | Create an entry. Body: `{user_id, content, title?, mood?}` |
| GET | `/journal/entries/{id}?user_id=` | Get a single entry |
| PATCH | `/journal/entries/{id}?user_id=` | Update an entry |
| DELETE | `/journal/entries/{id}?user_id=` | Delete an entry |
| POST | `/journal/search` | Semantic search. Body: `{user_id, query, k?}` |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Returns `{status: "ok"}` |
| GET | `/status` | Full system status: Ollama, models, features |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend framework** | FastAPI with uvicorn |
| **Agent orchestration** | LangGraph (StateGraph) |
| **LLM runtime** | Ollama (local, qwen2.5:7b) |
| **Vector search** | FAISS (IndexFlatIP) |
| **Keyword search** | rank-bm25 |
| **Reranking** | sentence-transformers CrossEncoder |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) |
| **Database** | SQLite with WAL mode |
| **Web search** | DuckDuckGo (ddgs) + trafilatura |
| **Chunking** | tiktoken (cl100k_base) |
| **Frontend** | React 19, Vite, Tailwind CSS |
| **Streaming** | Server-Sent Events (SSE) |

## Database Schema

SQLite with 7 tables:

- **users** — user profiles
- **conversations** — chat sessions per user
- **messages** — message history per conversation (role, content, timestamps)
- **journal_entries** — journal with title, content, mood, tags, embeddings
- **tasks** — tasks with title, status, priority, due dates
- **user_memories** — key-value facts with embeddings for semantic recall
- **calendar_events** — events with title, start/end times
