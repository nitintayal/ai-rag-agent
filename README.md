# AI Personal Assistant

**AI Personal assistant**

Use Gemini or OpenRouter free tiers in the cloud, or run Ollama entirely on your own machine. Either way, zero subscription fees and no third-party data access.

A full-stack AI personal assistant with chat, search your documents, manage tasks, keep a journal, track your calendar, and build persistent memory — all in one self-hostable app.

**Live Demo:** [iassistant.in](https://iassistant.in)

<!-- Replace the line below with your GIF path or GitHub video URL once recorded -->
![Demo — streaming chat and multi-tool call](demo.gif)

## Free Hosting Stack (everything has a free tier)

| Layer | Free option |
|-------|-------------|
| LLM | [Gemini 2.5 Flash](https://ai.google.dev) free tier · [OpenRouter](https://openrouter.ai) free models · [Ollama](https://ollama.com) local |
| Backend | [Render](https://render.com) free web service |
| Frontend | [Vercel](https://vercel.com) free tier |
| Database | [Supabase](https://supabase.com) free tier · SQLite locally |
| Web search | DuckDuckGo (no key needed) |
| Email | [Resend](https://resend.com) free tier (optional) |

## Features

- **Chat with real-time streaming** — token-by-token responses via Server-Sent Events (SSE)
- **Multi-tool per turn** — agent can call multiple tools in one message (e.g. "show my tasks and search journal")
- **RAG document search** — upload PDFs, TXT, XLSX, CSV and ask questions with hybrid retrieval (FAISS + BM25 + cross-encoder reranking)
- **Web search** — routes time-sensitive queries to DuckDuckGo (free) or Tavily (API key) with parallel page content extraction
- **Task management** — create, complete, filter, and track tasks with priorities, due dates, and recurrence (daily/weekly/monthly — completing a recurring task auto-creates the next one)
- **Task reminders** — due/overdue tasks trigger reminder emails (Resend) and Web Push notifications
- **Web Push notifications** — PWA push via VAPID/pywebpush with per-user subscription management
- **Journal** — personal journal with CRUD, mood tagging, and semantic search
- **Persistent memory** — remembers user preferences and facts across conversations
- **Calendar** — full event CRUD API with date-range queries, all-day events, and recurrence
- **Timezone-aware** — frontend sends the browser timezone with each chat message; date context in the routing prompt uses the user's local time
- **Conversation history** — multi-turn context with past chat sidebar
- **Intelligent routing** — single LLM call picks the right tool(s) and extracts arguments
- **Authentication** — JWT-based auth with email/password + Google OAuth
- **Email verification** — optional via Resend (configurable)
- **Per-user model selection** — each user can pick their own LLM provider/model in Settings, independent of the server default
- **Bring your own API key** — users can save a personal Gemini/OpenRouter API key in Settings, used instead of the server's key
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
│  /auth /chat /conversations /tasks /journal /calendar        │
│  /push /upload                                               │
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
    │OpenRouter│  └────┬────┘  └───┬─────┘
    │ /Ollama │        │           │
    └─────────┘       │           │
               ┌──────▼──────┐ ┌──▼────────┐
               │  RAG layer  │ │  Storage   │
               │ FAISS+BM25  │ │ SQLite/    │
               └─────────────┘ │ Supabase   │
                               └────────────┘
```

### Layered Architecture (8 layers)

```
API Layer  →  Auth Layer
           →  Agent Layer  →  LLM Layer (Gemini / OpenRouter / Ollama, per-user override)
                            →  Tool Layer  →  RAG Layer
                                           →  Storage Layer (plug-and-play)
                            →  Memory Layer →  Storage Layer
```

| Layer | Purpose | Key Files |
|-------|---------|-----------|
| **API** | FastAPI endpoints, SSE streaming, request schemas | `api/app.py`, `api/routes/` |
| **Auth** | JWT tokens, password hashing, Google OAuth, email verification | `auth/`, `api/routes/auth.py`, `api/routes/profile.py` |
| **Agent** | LangGraph graph, multi-tool orchestration, sync + streaming | `agent/graph.py`, `agent/nodes.py`, `agent/runner.py` |
| **LLM** | Gemini / OpenRouter / Ollama / Anthropic clients with retry + fallback, per-user provider/model/API-key overrides | `llm/factory.py`, `llm/gemini_client.py`, `llm/openrouter_client.py`, `llm/ollama_client.py`, `llm/anthropic_client.py` |
| **Tools** | 6 tools with uniform `BaseTool` interface and registry | `tools/base.py`, `tools/registry.py`, `tools/*.py` |
| **Memory** | Conversation history + long-term user facts + context builder | `memory/` |
| **RAG** | FAISS + BM25 hybrid search, cross-encoder reranking, ingestion | `rag/` |
| **Storage** | Plug-and-play database with abstract base + SQLite/Supabase backends | `storage/factory.py`, `storage/backends/` |

### Tools

| Tool | Description |
|------|-------------|
| `rag` | Hybrid search over uploaded documents with reranking |
| `web` | Web search via DuckDuckGo or Tavily, with parallel page content extraction |
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

Switch between local and cloud LLMs via a global default, or let each user pick their own in Settings:

```
LLM_PROVIDER=gemini       # Google Gemini API (cloud, free tier)
LLM_PROVIDER=openrouter   # OpenRouter — access to multiple free models via one key
LLM_PROVIDER=ollama       # Local Ollama (requires 8GB+ RAM)
LLM_PROVIDER=anthropic    # Anthropic Claude (paid per token, requires ANTHROPIC_API_KEY)
```

Gemini and OpenRouter clients include retry + automatic fallback across multiple models if the primary one is rate-limited or unavailable (Gemini: 2.5-flash → 2.0-flash → 2.0-flash-lite; OpenRouter: rotates across several free `:free` models). The Anthropic client uses Claude Haiku 4.5 (cheapest Claude model). Per-user overrides are stored on the `users` table (`llm_provider`, `llm_model`, `llm_api_key`) and set via `PATCH /auth/llm-settings` — the agent resolves the user's choice (and personal API key, if saved) first, falling back to the global default if their provider isn't configured.

### Web Search Provider

```
WEB_SEARCH_PROVIDER=ddgs     # DuckDuckGo via scraping (free, no key needed)
WEB_SEARCH_PROVIDER=tavily   # Tavily API (faster, cleaner results, requires TAVILY_API_KEY)
```

## Project Structure

```
ai-rag-agent/
├── api/                              # API Layer
│   ├── app.py                        #   FastAPI app, CORS, lifespan
│   ├── dependencies.py               #   Auth dependency (get_current_user)
│   ├── routes/
│   │   ├── auth.py                   #   Register, login, Google OAuth, forgot/reset password
│   │   ├── profile.py                #   /me, profile update, LLM settings, change password
│   │   ├── chat.py                   #   POST /chat (SSE streaming)
│   │   ├── conversations.py          #   Chat history CRUD
│   │   ├── documents.py              #   File upload/delete
│   │   ├── journal.py                #   Journal CRUD + search
│   │   ├── tasks.py                  #   Task CRUD + due-date reminders (email + push)
│   │   ├── calendar.py               #   Calendar event CRUD
│   │   ├── push.py                   #   Web Push subscribe/unsubscribe + send helper
│   │   └── health.py                 #   Health + status
│   └── schemas/                      #   Pydantic models (auth.py, chat.py, tasks.py)
│
├── auth/                             # Auth Layer
│   ├── passwords.py                  #   bcrypt hashing
│   ├── jwt_utils.py                  #   JWT create/decode
│   ├── google_oauth.py               #   Google ID token verification
│   ├── email.py                      #   Resend email integration (verification, reset, task reminders)
│   ├── rate_limit.py                 #   Shared IP rate limiter
│   └── verification.py               #   Verification code generation/validation
│
├── agent/                            # Agent Layer
│   ├── graph.py                      #   LangGraph StateGraph
│   ├── state.py                      #   AgentState TypedDict
│   ├── nodes.py                      #   route, execute_tool(s), generate, extract_memory
│   └── runner.py                     #   Sync + streaming entry points
│
├── llm/                              # LLM Layer
│   ├── factory.py                    #   Returns Gemini/OpenRouter/Ollama client; per-user provider/model/API-key override
│   ├── gemini_client.py              #   Gemini API with retry + model fallback
│   ├── openrouter_client.py          #   OpenRouter API with retry + free-model fallback chain
│   ├── ollama_client.py              #   Ollama REST client (sync + async + streaming)
│   ├── prompts.py                    #   All prompt templates
│   └── model_manager.py              #   Ollama model availability checks
│
├── tools/                            # Tool Layer
│   ├── base.py                       #   BaseTool ABC, ToolResult, ToolDefinition
│   ├── registry.py                   #   Tool registry
│   ├── rag_tool.py                   #   RAG hybrid search
│   ├── web_tool.py                   #   Web search dispatcher (ddgs/tavily)
│   ├── web_search/
│   │   ├── ddgs_search.py            #   DuckDuckGo scraping + trafilatura extraction
│   │   └── tavily_search.py          #   Tavily API search
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
│   │   ├── memory_repo.py
│   │   ├── calendar_repo.py
│   │   ├── verification_repo.py
│   │   └── push_repo.py
│   └── backends/
│       ├── base.py                   #   Abstract base classes for all repos
│       ├── embedding_utils.py        #   Safe embedding + shared search-text helper (ML-optional)
│       ├── sqlite/                   #   SQLite implementation (8 repo modules)
│       └── supabase/                 #   Supabase implementation (8 repo modules + client.py + schema.sql)
│
├── rag/                               # Retrieval Layer (consolidated)
│   ├── vector_store.py               #   FAISS + BM25 hybrid search
│   ├── embeddings.py                 #   SentenceTransformer wrapper
│   ├── reranker.py                   #   Cross-encoder reranking
│   ├── load_documents.py             #   PDF, TXT, XLSX, CSV loaders
│   ├── chunk_documents.py            #   Token-based chunking (tiktoken)
│   └── ingest_documents.py           #   Ingestion orchestration
│
├── docs/
│   └── ARCHITECTURE.md               #   Deep technical reference
│
├── configs/config.py                 #   Pydantic BaseSettings
├── scripts/generate_vapid_keys.py    #   One-time VAPID key generation for Web Push
├── start.py                          #   Cloud entry point (Render's configured start command)
├── render.yaml                       #   Render blueprint reference
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

### Option 2: Cloud Deployment (Gemini/OpenRouter + Supabase)

**Backend (Render):**
1. Push to GitHub
2. Create Render Web Service → connect repo
3. Build: `pip install -r requirements-cloud.txt`
4. Start: `python start.py`
5. Set env vars: `LLM_PROVIDER=gemini` (or `openrouter`/`anthropic`), `GOOGLE_API_KEY` (or `OPENROUTER_API_KEY`/`ANTHROPIC_API_KEY`), `DB_BACKEND=supabase`, `SUPABASE_URL`, `SUPABASE_KEY`, `JWT_SECRET`, `CORS_ORIGINS`

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
| `LLM_PROVIDER` | `gemini` | `gemini`, `openrouter`, `ollama`, or `anthropic` — global default (users can override in Settings) |
| `GOOGLE_API_KEY` | — | Gemini API key (when provider=gemini) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `OPENROUTER_API_KEY` | — | OpenRouter API key (when provider=openrouter) |
| `OPENROUTER_MODEL` | `meta-llama/llama-3.3-70b-instruct:free` | OpenRouter model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_CHAT_MODEL` | `qwen2.5:7b` | Ollama model name |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (when provider=anthropic) |
| `ANTHROPIC_MODEL` | `claude-haiku-4-5` | Anthropic model name |
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
| `RESEND_FROM_EMAIL` | `ai-personal-agent@resend.dev` | Sender email |
| `FRONTEND_URL` | `http://localhost:5173` | For email verification links |
| **Push Notifications** | | |
| `VAPID_PRIVATE_KEY` | — | VAPID private key (generate with `scripts/generate_vapid_keys.py`) |
| `VAPID_PUBLIC_KEY` | — | VAPID public key (served to the frontend) |
| `VAPID_CLAIMS_EMAIL` | `mailto:admin@example.com` | VAPID claims contact |
| **Web Search** | | |
| `WEB_SEARCH_PROVIDER` | `ddgs` | `ddgs` (free) or `tavily` (API key, faster) |
| `TAVILY_API_KEY` | — | Tavily API key (when provider=tavily) |
| `WEB_SEARCH_MAX_RESULTS` | `3` | Results per query |
| **Retrieval** | | |
| `VECTOR_WEIGHT` | `0.7` | Vector search weight in hybrid |
| `BM25_WEIGHT` | `0.3` | BM25 weight in hybrid |
| `HYBRID_K` | `10` | Candidates from hybrid search |
| `RERANK_K` | `5` | Documents after reranking |
| `MIN_HYBRID_SCORE` | `0.0` | Minimum hybrid score |
| `MIN_RERANK_SCORE` | `-9999.0` | Minimum rerank score (disabled by default) |
| **Other** | | |
| `CONVERSATION_HISTORY_LIMIT` | `20` | Messages per conversation turn |
| `MEMORY_EXTRACTION_ENABLED` | `true` | Auto-extract user facts |
| `API_PORT` | `8000` | Server port |
| `DEBUG` | `false` | Enable auto-reload |

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register with email/password |
| POST | `/auth/login` | Login |
| POST | `/auth/google` | Google OAuth login |
| POST | `/auth/forgot-password` | Send reset email |
| POST | `/auth/reset-password` | Reset with code |
| POST | `/auth/verify-email` | Verify email with code |
| GET | `/auth/me` | Get current user |
| PATCH | `/auth/profile` | Update display name |
| POST | `/auth/change-password` | Change password |
| PATCH | `/auth/llm-settings` | Set per-user LLM provider/model/API key |
| GET | `/auth/llm-settings/available` | List available models per provider |

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
| POST | `/tasks` | Create task (priority, due date, recurrence) |
| PATCH | `/tasks/{id}` | Update task (completing a recurring task spawns the next occurrence) |
| DELETE | `/tasks/{id}` | Delete task |
| GET | `/tasks/send-reminders` | Send email + push reminders for due/overdue tasks |

### Calendar
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/calendar/events` | List events (optional `start`/`end` range) |
| POST | `/calendar/events` | Create event (all-day, location, recurrence) |
| GET | `/calendar/events/{id}` | Get event |
| PATCH | `/calendar/events/{id}` | Update event |
| DELETE | `/calendar/events/{id}` | Delete event |

### Push Notifications
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/push/vapid-public-key` | Get VAPID public key for subscription |
| POST | `/push/subscribe` | Save a push subscription |
| DELETE | `/push/subscribe` | Remove a push subscription |

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
| **LLM** | Google Gemini / OpenRouter (cloud, free tiers) / Ollama (local) — per-user selectable |
| **Database** | Supabase (cloud) / SQLite (local) |
| **Auth** | JWT + bcrypt + Google OAuth |
| **Email** | Resend |
| **Push** | Web Push (pywebpush + VAPID) |
| **Vector search** | FAISS + rank-bm25 + CrossEncoder |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) |
| **Web search** | DuckDuckGo (ddgs) + trafilatura, or Tavily API |
| **Frontend** | React 19, Vite, Tailwind CSS |
| **Hosting** | Render (backend) + Vercel (frontend) |

## Database Schema

9 tables (same schema across SQLite and Supabase):

| Table | Purpose |
|-------|---------|
| `users` | User profiles with email, password hash, auth provider, LLM preferences + personal API key |
| `conversations` | Chat sessions per user |
| `messages` | Message history per conversation |
| `journal_entries` | Journal with title, content, mood, tags, embeddings |
| `tasks` | Tasks with status, priority, due dates, recurrence, reminder tracking |
| `user_memories` | Key-value user facts with embeddings |
| `calendar_events` | Events with start/end times, all-day flag, location, recurrence |
| `verification_codes` | Email verification and password reset codes |
| `push_subscriptions` | Web Push subscriptions (endpoint + encryption keys) per user |
