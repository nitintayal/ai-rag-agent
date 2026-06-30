# Architecture Deep Dive

## System Overview

```
User (browser/mobile)
  │
  ├── React Frontend (Vercel)
  │     ├── Auth (JWT in localStorage)
  │     ├── SSE streaming chat
  │     ├── Tasks / Journal / Settings panels
  │     └── Dark mode + Voice input + PWA
  │
  └── FastAPI Backend (Render)
        ├── Auth Layer (JWT + Google OAuth + Resend)
        ├── Agent Layer (LangGraph)
        ├── LLM Layer (Gemini / OpenRouter / Ollama, per-user selectable)
        ├── Tool Layer (6 tools)
        ├── Memory Layer (conversation + long-term)
        └── Storage Layer (SQLite / Supabase)
```

---

## Request Lifecycle: Chat Message

```
1. Frontend sends POST /chat with {question, conversation_id}
   └── Authorization: Bearer <jwt>

2. api/routes/chat.py
   ├── Extracts user from JWT
   ├── Creates conversation if new (auto-titled from first message)
   └── Returns StreamingResponse (SSE)

3. agent/runner.py → run_agent_stream()
   ├── ROUTE: Single LLM call → {"tools": [{tool, args}]}
   │   ├── LLM routing prompt includes all 6 tool options
   │   └── Keyword fallback if LLM fails
   │
   ├── EXECUTE: Runs selected tool(s)
   │   ├── Single tool: tool.execute(user_id, query, **args)
   │   └── Multi-tool: runs all, merges context with [TOOL_NAME] headers
   │
   ├── BUILD CONTEXT:
   │   ├── Load conversation history (last 20 messages)
   │   ├── Load user memory (semantic recall of relevant facts)
   │   └── Merge: system prompt + user memory + history + tool context
   │
   ├── STREAM: LLM generates answer token-by-token
   │   └── Each token → SSE event: data: {"token": "..."}
   │
   ├── SAVE: Store user message + assistant response in DB
   │
   └── EXTRACT MEMORY: (optional, after streaming)
       └── LLM extracts personal facts → stored for future conversations

4. Frontend receives SSE events → renders incrementally
```

---

## Data Flow: Authentication

```
Register:
  POST /auth/register {email, password, name}
  ├── Validate input
  ├── Hash password (bcrypt)
  ├── Create user in DB
  ├── If REQUIRE_EMAIL_VERIFICATION=true:
  │   ├── Generate verification code
  │   ├── Send email via Resend
  │   └── Return {status: "verification_sent"}
  └── Else: Return {token, user}

Login:
  POST /auth/login {email, password}
  ├── Find user by email
  ├── Verify password (bcrypt)
  ├── If email not verified + verification required → 403
  └── Return {token, user}

Google OAuth:
  POST /auth/google {id_token}
  ├── Verify token with Google tokeninfo endpoint
  ├── Check audience matches GOOGLE_OAUTH_CLIENT_ID
  ├── Create or find user by email
  ├── Auto-verify email
  └── Return {token, user}

Every protected request:
  Authorization: Bearer <jwt>
  → api/dependencies.py → decode JWT → find user → inject into route
  → If user missing from DB (Render reset), recreate from JWT payload
```

---

## Storage Layer: Plug-and-Play Pattern

```
                    storage/repositories/user_repo.py
                              │
                    def ensure_user(user_id, name):
                        return get_backend().user.ensure_user(user_id, name)
                              │
                    storage/factory.py → get_backend()
                              │
                    ┌─────────┴─────────┐
                    │                   │
        DB_BACKEND=sqlite     DB_BACKEND=supabase
                    │                   │
        backends/sqlite/       backends/supabase/
        user_repo.py           user_repo.py
        (raw SQL)              (supabase-py REST)
```

### Why This Pattern

- **No interface leakage**: Routes, agent, tools never know which DB is active
- **No code duplication**: Dispatchers are 5-line functions
- **Easy to add**: New backend = new folder + `elif` in factory
- **Testable**: Can mock the backend for testing

### Adding a Backend (e.g., PostgreSQL)

```python
# storage/backends/postgres/__init__.py
from storage.backends.base import StorageBackend
from storage.backends.postgres import user_repo, conversation_repo, ...

def create_backend():
    # setup connection pool
    return StorageBackend(user=user_repo, conversation=conversation_repo, ...)

# Each repo module: same function signatures as base.py
# Use psycopg2 or asyncpg internally
```

---

## LLM Layer: Provider Abstraction

```
llm/factory.py → get_llm_client(provider=None, model=None)
       │         get_llm_client_for_user(user)  ← resolves user["llm_provider"/"llm_model"] first
       │
       ├── provider=gemini → GeminiClient
       │   ├── google-genai SDK
       │   ├── Retry: 2 attempts per model
       │   ├── Fallback chain: 2.5-flash → 2.0-flash → 2.0-flash-lite
       │   └── Handles 503/429 gracefully
       │
       ├── provider=openrouter → OpenRouterClient
       │   ├── OpenAI-compatible REST API (httpx)
       │   ├── Retry: 2 attempts per model on 429
       │   ├── Fallback chain across multiple free `:free` models
       │   └── 404 (deprecated/renamed model) skips straight to next model, no wasted retry
       │
       └── provider=ollama → OllamaClient
           ├── httpx → localhost:11434/api/chat
           ├── Real token streaming via chunked response
           └── Model management (pull, list, check)

All three implement the same interface:
  .chat(messages, model, system, format) → str
  .chat_stream(messages, ...) → AsyncIterator[str]
  .generate(prompt, ...) → str
  .chat_full_async(messages, ...) → str

Per-user overrides: PATCH /auth/llm-settings sets users.llm_provider / users.llm_model.
agent/state.py::AgentState carries llm_provider/llm_model through every node that calls
the LLM (route, generate, extract_memory) via agent/nodes.py::_get_llm(state).
If the user's chosen provider has no API key configured, falls back to the global default.
```

---

## Tool System

```
tools/base.py:
  ToolDefinition(name, description)
  ToolResult(context, sources, data, error)
  BaseTool(ABC) → .execute(user_id, **kwargs) → ToolResult

tools/registry.py:
  get_all_tools() → [RagTool, WebTool, JournalTool, TaskTool, MemoryTool, CalendarTool]
  get_tool("web") → WebTool instance

Agent routing (llm/prompts.py):
  Single LLM call returns: {"tools": [{"tool": "task", "args": {"action": "create", "title": "..."}}]}
  Multi-tool: {"tools": [{"tool": "task", ...}, {"tool": "journal", ...}]}
```

### Tool Execution Flow

```
question: "Create a task and search my journal for meetings"
  │
  ├── Route LLM → {"tools": [
  │     {"tool": "task", "args": {"action": "create", "title": "New task"}},
  │     {"tool": "journal", "args": {"action": "search", "query": "meetings"}}
  │   ]}
  │
  ├── Execute both:
  │   ├── TaskTool.execute() → "Task created: New task"
  │   └── JournalTool.execute() → "[2024-01-15] Team meeting notes..."
  │
  ├── Merge context:
  │   [TASK results]
  │   Task created: New task
  │
  │   [JOURNAL results]
  │   [2024-01-15] Team meeting notes...
  │
  └── Generate → LLM produces final answer using merged context
```

---

## Memory System

```
Short-term (per conversation):
  memory/conversation_memory.py
  ├── Stores every message in DB (via conversation_repo)
  ├── Loads last 20 messages as sliding window
  └── Injected into LLM context on every turn

Long-term (cross-session):
  memory/long_term_memory.py
  ├── After each turn, LLM extracts personal facts
  │   "I'm a data scientist" → {key: "profession", value: "data scientist"}
  ├── Stored with embeddings for semantic recall
  ├── On each turn, relevant facts recalled via embedding search
  └── Injected into system prompt: "Known facts about this user: ..."

Context assembly:
  memory/context_builder.py
  └── build_messages(question, history, user_memory, tool_context)
      → [system + user_memory, ...history, tool_context + question]
```

---

## Frontend Architecture

```
React 19 (Vite + Tailwind CSS)

State Management:
  AuthProvider (useAuth hook)  → user, token, login/register/logout
  ThemeProvider (useTheme hook) → dark mode toggle

Routing: No React Router — view switching via activeView state
  "chat" → ChatWindow
  "tasks" → TasksPanel
  "journal" → JournalPanel
  "settings" → SettingsPanel

SSE Streaming:
  fetch("/chat", {method: "POST"})
  → ReadableStream → parse "data: {token}" lines
  → Update message state incrementally

Auth Flow:
  localStorage: token + user (JSON)
  Every API call: Authorization: Bearer <token>
  Page load: trust cached user, no /auth/me call (prevents flash)
  Google OAuth: redirect → hash fragment → parse id_token → /auth/google
```

---

## Security Model

| Layer | Protection |
|-------|-----------|
| Passwords | bcrypt (salted hash) |
| Tokens | JWT with configurable secret, 72h expiry |
| API | All data routes require valid JWT |
| Upload | Auth required, file type + size validation |
| Login | Rate limited (5/min per IP) |
| CORS | Configurable allowed origins |
| Google OAuth | Token audience verification |
| SQL | All queries parameterized (no injection) |
| Secrets | Never in git (.env in .gitignore) |
| Frontend | Token in localStorage (XSS risk accepted for personal use) |

---

## Deployment Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Vercel     │────▶│   Render     │────▶│  Supabase    │
│  (Frontend)  │     │  (Backend)   │     │  (Database)  │
│  React SPA   │     │  FastAPI     │     │  Postgres    │
│  CDN/Edge    │     │  Python 3.12 │     │  REST API    │
└─────────────┘     │              │     └──────────────┘
                    │         ┌────┘
                    │         ▼
                    │  ┌──────────────────────┐
                    │  │  Gemini / OpenRouter  │
                    │  │  (LLM, per-user pick) │
                    │  └──────────────────────┘
                    └──────────────────

Free tier limits:
  Vercel: Unlimited static hosting
  Render: 750 hrs/month, sleeps after 15min idle
  Supabase: 500MB, 2 projects
  Gemini: 500 req/day (2.5-flash), 1500/day (2.0-flash)
  OpenRouter: Per-model daily limits on :free models, varies — fallback chain mitigates this
```

---

## Design Decisions

| Decision | Why |
|----------|-----|
| SQLite as default | Zero config, works everywhere, good enough for personal use |
| Supabase over raw Postgres | Free tier, REST API (no connection pool needed), auth features |
| Gemini over OpenAI | Generous free tier, no credit card needed |
| JWT over sessions | Stateless, works with any backend, no session store needed |
| LangGraph over raw loop | Structured graph, easy to add nodes, built-in state management |
| Plug-and-play storage | Learned from the original project — journal had sqlite/postgres with factory, generalized it |
| Lazy ML imports | Cloud deployment can't install torch (2GB+), so embeddings are optional |
| No React Router | Single-page personal tool, URL routing adds complexity without value |
| localStorage for auth | Simpler than httpOnly cookies for a personal assistant |
