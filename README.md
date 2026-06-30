# AI Personal Assistant

A full-stack AI personal assistant with chat, RAG document search, web search, journal, task management, persistent memory, calendar, and authentication — deployable locally with Ollama or in the cloud with Gemini + Supabase.

**Live Demo:** [iassistant.in](https://iassistant.in)

## Features

- **Chat with real-time streaming** — token-by-token responses via Server-Sent Events (SSE)
- **Multi-tool per turn** — agent can call multiple tools in one message (e.g. "show my tasks and search journal")
- **RAG document search** — upload PDFs, TXT, XLSX, CSV and ask questions with hybrid retrieval (FAISS + BM25 + cross-encoder reranking)
- **Web search** — routes time-sensitive queries to DuckDuckGo with parallel page content extraction
- **Task management** — create, complete, filter, and track tasks with priorities and due dates
- **Journal** — personal journal with CRUD, mood tagging, and semantic search
- **Persistent memory** — remembers user preferences and facts across conversations
- **Calendar** — simple event management with date/time tracking
- **Conversation history** — multi-turn context with past chat sidebar
- **Intelligent routing** — single LLM call picks the right tool(s) and extracts arguments
- **Authentication** — JWT-based auth with email/password + Google OAuth
- **Email verification** — optional via Resend (configurable)
- **Dark mode** — system-aware with manual toggle
- **Voice input** — browser Speech-to-Text for hands-free input
- **Mobile PWA** — installable as a native app on iPhone/Android
- **Plug-and-play database** — switch between SQLite, Supabase, or add your own backend via config

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend: React 19 + Tailwind CSS + Vite                    │
│  Chat (SSE) │ Tasks │ Journal │ Settings │ Dark Mode │ Voice  │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────▼───────────────────────────────────┐
│  API Layer (FastAPI)                                         │
│  /auth  /chat  /conversations  /tasks  /journal  /upload     │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│  Agent Layer (LangGraph StateGraph)                          │
│  route → execute_tool(s) → generate → extract_memory         │
└────────┬────────────┬────────────┬───────────────────────────┘
         │            │            │
    ┌────▼────┐  ┌────▼────┐  ┌───▼─────┐
    │  LLM    │  │  Tools  │  │  Memory │
    │ Gemini/ │  │  (6)    │  │         │
    │ Ollama  │  └────┬────┘  └───┬─────┘
    └─────────┘       │           │
               ┌──────▼──────┐ ┌──▼────────┐
               │  Retrieval  │ │  Storage   │
               │ FAISS+BM25  │ │ SQLite/    │
               └─────────────┘ │ Supabase   │
                               └────────────┘
```

### Layered Architecture (8 layers)

```
API Layer  →  Auth Layer
           →  Agent Layer  →  LLM Layer (Gemini / Ollama)
                            →  Tool Layer  →  Retrieval Layer
                                           →  Storage Layer (plug-and-play)
                            →  Memory Layer →  Storage Layer
```

| Layer | Purpose | Key Files |
|-------|---------|-----------|
| **API** | FastAPI endpoints, SSE streaming, request schemas | `api/app.py`, `api/routes/` |
| **Auth** | JWT tokens, password hashing, Google OAuth, email verification | `auth/`, `api/routes/auth.py` |
| **Agent** | LangGraph graph, multi-tool orchestration, sync + streaming | `agent/graph.py`, `agent/nodes.py`, `agent/runner.py` |
| **LLM** | Gemini + Ollama clients, prompt templates, model management | `llm/factory.py`, `llm/gemini_client.py`, `llm/ollama_client.py` |
| **Tools** | 6 tools with uniform `BaseTool` interface and registry | `tools/base.py`, `tools/registry.py`, `tools/*.py` |
| **Memory** | Conversation history + long-term user facts + context builder | `memory/` |
| **Retrieval** | FAISS + BM25 hybrid search, cross-encoder reranking, ingestion | `retrieval/`, `embeddings/`, `ranker/`, `ingestion/` |
| **Storage** | Plug-and-play database with abstract base + SQLite/Supabase backends | `storage/factory.py`, `storage/backends/` |

### Tools

| Tool | Description |
|------|-------------|
| `rag` | Hybrid search over uploaded documents with reranking |
| `web` | DuckDuckGo search with parallel page content extraction |
| `journal` | Journal entries with semantic search |
| `task` | Task/reminder management with status, priority, due dates |
| `memory` | Store and recall user preferences and facts |
| `calendar` | Calendar event management |

### Plug-and-Play Database

The storage layer uses an abstract base class pattern. Switch backends by changing one env var:

```
DB_BACKEND=sqlite     # Local file-based (default)
DB_BACKEND=supabase   # Cloud Postgres via Supabase
```

To add a new backend (Postgres, MongoDB, MySQL, etc.):
1. Create `storage/backends/mydb/` with 5 repo modules
2. Each module implements the same function signatures (see `storage/backends/base.py`)
3. Add an `elif` in `storage/factory.py`
4. Set `DB_BACKEND=mydb`

Zero changes to API routes, agent, memory, tools, or frontend.

### LLM Provider

Switch between local and cloud LLMs:

```
LLM_PROVIDER=gemini   # Google Gemini API (cloud, free tier)
LLM_PROVIDER=ollama   # Local Ollama (requires 8GB+ RAM)
```

Gemini client includes retry + fallback across models (2.5-flash → 2.0-flash → 2.0-flash-lite).

## Project Structure

```
ai-rag-agent/
├── api/                              # API Layer
│   ├── app.py                        #   FastAPI app, CORS, lifespan
│   ├── dependencies.py               #   Auth dependency (get_current_user)
│   ├── routes/
│   │   ├── auth.py                   #   Register, login, Google OAuth, forgot/reset password
│   │   ├── chat.py                   #   POST /chat (SSE streaming)
│   │   ├── conversations.py          #   Chat history CRUD
│   │   ├── documents.py              #   File upload/delete
│   │   ├── journal.py                #   Journal CRUD + search
│   │   ├── tasks.py                  #   Task CRUD
│   │   └── health.py                 #   Health + status
│   └── schemas/                      #   Pydantic models
│
├── auth/                             # Auth Layer
│   ├── passwords.py                  #   bcrypt hashing
│   ├── jwt_utils.py                  #   JWT create/decode
│   ├── google_oauth.py               #   Google ID token verification
│   └── email.py                      #   Resend email integration
│
├── agent/                            # Agent Layer
│   ├── graph.py                      #   LangGraph StateGraph
│   ├── state.py                      #   AgentState TypedDict
│   ├── nodes.py                      #   route, execute_tool(s), generate, extract_memory
│   └── runner.py                     #   Sync + streaming entry points
│
├── llm/                              # LLM Layer
│   ├── factory.py                    #   Returns Gemini or Ollama client based on config
│   ├── gemini_client.py              #   Gemini API with retry + model fallback
│   ├── ollama_client.py              #   Ollama REST client (sync + async + streaming)
│   ├── prompts.py                    #   All prompt templates
│   └── model_manager.py              #   Ollama model availability checks
│
├── tools/                            # Tool Layer
│   ├── base.py                       #   BaseTool ABC, ToolResult, ToolDefinition
│   ├── registry.py                   #   Tool registry
│   ├── rag_tool.py                   #   RAG hybrid search
│   ├── web_tool.py                   #   Web search (DuckDuckGo + trafilatura)
│   ├── journal_tool.py               #   Journal CRUD + search
│   ├── task_tool.py                  #   Task management
│   ├── memory_tool.py                #   User memory store/recall
│   └── calendar_tool.py              #   Calendar events
│
├── memory/                           # Memory Layer
│   ├── conversation_memory.py        #   Per-session message history
│   ├── long_term_memory.py           #   Cross-session user facts
│   └── context_builder.py            #   Builds LLM message list
│
├── storage/                          # Storage Layer (plug-and-play)
│   ├── factory.py                    #   Backend picker (sqlite/supabase/...)
│   ├── database.py                   #   SQLite engine + schema
│   ├── repositories/                 #   Public API (thin dispatchers)
│   │   ├── user_repo.py
│   │   ├── conversation_repo.py
│   │   ├── journal_repo.py
│   │   ├── task_repo.py
│   │   └── memory_repo.py
│   └── backends/
│       ├── base.py                   #   Abstract base classes for all repos
│       ├── embedding_utils.py        #   Safe embedding helper (ML-optional)
│       ├── sqlite/                   #   SQLite implementation
│       │   ├── user_repo.py
│       │   ├── conversation_repo.py
│       │   ├── journal_repo.py
│       │   ├── task_repo.py
│       │   └── memory_repo.py
│       └── supabase/                 #   Supabase implementation
│           ├── client.py             #   Supabase client singleton
│           ├── schema.sql            #   Table creation SQL
│           ├── user_repo.py
│           ├── conversation_repo.py
│           ├── journal_repo.py
│           ├── task_repo.py
│           └── memory_repo.py
│
├── retrieval/                        # Retrieval Layer
│   └── vector_store.py               #   FAISS + BM25 hybrid search
├── embeddings/
│   └── sentence_embeddings.py        #   SentenceTransformer wrapper
├── ranker/
│   └── cross_encoder.py              #   Cross-encoder reranking
├── ingestion/                        #   Document ingestion pipeline
│   ├── load_documents.py             #   PDF, TXT, XLSX, CSV loaders
│   ├── chunk_documents.py            #   Token-based chunking (tiktoken)
│   └── ingest_documents.py           #   Orchestration
│
├── mcp_servers/                      #   MCP Tool Servers (stdio)
│   ├── servers.json
│   ├── client/mcp_client.py
│   └── servers/
│       ├── rag_server.py
│       ├── web_server.py
│       └── journal_server.py
│
├── configs/config.py                 #   Pydantic BaseSettings
├── start.py                          #   Cloud entry point (Render)
├── render.yaml                       #   Render blueprint
├── .env.example                      #   Config template
├── requirements.txt                  #   Full dependencies (local)
└── requirements-cloud.txt            #   Cloud dependencies (no torch)
```

## Getting Started

### Option 1: Local Development (Ollama)

```bash
# Clone
git clone https://github.com/nitintayal/ai-rag-agent.git
cd ai-rag-agent

# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Set LLM_PROVIDER=ollama, DB_BACKEND=sqlite

# Install Ollama + model
# Download from https://ollama.com/download
ollama pull qwen2.5:7b

# Run
python -m api.app
```

### Option 2: Cloud Deployment (Gemini + Supabase)

**Backend (Render):**
1. Push to GitHub
2. Create Render Web Service → connect repo
3. Build: `pip install -r requirements-cloud.txt`
4. Start: `PYTHONPATH=/opt/render/project/src python start.py`
5. Set env vars: `LLM_PROVIDER=gemini`, `GOOGLE_API_KEY`, `DB_BACKEND=supabase`, `SUPABASE_URL`, `SUPABASE_KEY`, `JWT_SECRET`

**Frontend (Vercel):**
1. Push `ai-rag-ui` to GitHub
2. Import in Vercel
3. Set `VITE_API_BASE=https://your-render-url.onrender.com`

**Supabase:**
1. Create project at [supabase.com](https://supabase.com)
2. Run `storage/backends/supabase/schema.sql` in SQL Editor
3. Copy URL + service_role key to Render env vars

### Frontend Setup

```bash
cd ai-rag-ui
npm install
npm run dev
```

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| **LLM** | | |
| `LLM_PROVIDER` | `ollama` | `ollama` or `gemini` |
| `GOOGLE_API_KEY` | — | Gemini API key (when provider=gemini) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_CHAT_MODEL` | `qwen2.5:7b` | Ollama model name |
| **Database** | | |
| `DB_BACKEND` | `sqlite` | `sqlite` or `supabase` |
| `DATABASE_PATH` | `data/db/assistant.db` | SQLite file path |
| `SUPABASE_URL` | — | Supabase project URL |
| `SUPABASE_KEY` | — | Supabase service_role key |
| **Auth** | | |
| `JWT_SECRET` | `change-me...` | JWT signing secret |
| `GOOGLE_OAUTH_CLIENT_ID` | — | For Google login |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `REQUIRE_EMAIL_VERIFICATION` | `false` | Gate login behind email verify |
| `RESEND_API_KEY` | — | Resend.com API key for emails |
| `RESEND_FROM_EMAIL` | `onboarding@resend.dev` | Sender email |
| `FRONTEND_URL` | `http://localhost:5173` | For email verification links |
| **Retrieval** | | |
| `VECTOR_WEIGHT` | `0.7` | Vector search weight in hybrid |
| `BM25_WEIGHT` | `0.3` | BM25 weight in hybrid |
| `HYBRID_K` | `10` | Candidates from hybrid search |
| `RERANK_K` | `5` | Documents after reranking |
| `MIN_HYBRID_SCORE` | `0.15` | Minimum hybrid score |
| `MIN_RERANK_SCORE` | `0.10` | Minimum rerank score |
| **Other** | | |
| `CONVERSATION_HISTORY_LIMIT` | `20` | Messages per conversation turn |
| `MEMORY_EXTRACTION_ENABLED` | `true` | Auto-extract user facts |
| `WEB_SEARCH_MAX_RESULTS` | `3` | DuckDuckGo results per query |
| `API_PORT` | `8000` | Server port |
| `DEBUG` | `false` | Enable auto-reload |

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register with email/password |
| POST | `/auth/login` | Login |
| POST | `/auth/google` | Google OAuth login |
| GET | `/auth/me` | Get current user |
| PATCH | `/auth/profile` | Update display name |
| POST | `/auth/change-password` | Change password |
| POST | `/auth/forgot-password` | Send reset email |
| POST | `/auth/reset-password` | Reset with code |
| POST | `/auth/verify-email` | Verify email with code |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | SSE streaming chat |
| POST | `/chat/sync` | Non-streaming chat |
| GET | `/conversations` | List past conversations |
| GET | `/conversations/{id}/messages` | Load conversation messages |
| DELETE | `/conversations/{id}` | Delete conversation |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tasks` | List tasks (filterable by status) |
| POST | `/tasks` | Create task |
| PATCH | `/tasks/{id}` | Update task |
| DELETE | `/tasks/{id}` | Delete task |

### Journal
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/journal/entries` | List entries (paginated) |
| POST | `/journal/entries` | Create entry |
| PATCH | `/journal/entries/{id}` | Update entry |
| DELETE | `/journal/entries/{id}` | Delete entry |
| POST | `/journal/search` | Semantic search |

### Documents & System
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload` | Upload document |
| DELETE | `/delete?source=` | Remove document |
| GET | `/health` | Health check |
| GET | `/status` | System status |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Python, FastAPI, LangGraph |
| **LLM** | Google Gemini (cloud) / Ollama (local) |
| **Database** | Supabase (cloud) / SQLite (local) |
| **Auth** | JWT + bcrypt + Google OAuth |
| **Email** | Resend |
| **Vector search** | FAISS + rank-bm25 + CrossEncoder |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) |
| **Web search** | DuckDuckGo (ddgs) + trafilatura |
| **Frontend** | React 19, Vite, Tailwind CSS |
| **Hosting** | Render (backend) + Vercel (frontend) |

## Database Schema

8 tables (same schema across SQLite and Supabase):

| Table | Purpose |
|-------|---------|
| `users` | User profiles with email, password hash, auth provider |
| `conversations` | Chat sessions per user |
| `messages` | Message history per conversation |
| `journal_entries` | Journal with title, content, mood, tags, embeddings |
| `tasks` | Tasks with status, priority, due dates |
| `user_memories` | Key-value user facts with embeddings |
| `calendar_events` | Events with start/end times |
| `verification_codes` | Email verification and password reset codes |
