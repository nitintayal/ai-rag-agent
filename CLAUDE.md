# CLAUDE.md — AI Agent Context

This file helps AI coding agents (Claude Code, Copilot, etc.) understand the project.

## What This Is

An AI personal assistant with chat, RAG, web search, tasks (with recurrence + reminders), journal, memory, calendar, and Web Push notifications. FastAPI backend + React frontend. Deployed on Render (backend) + Vercel (frontend), custom domain via Supabase-backed cloud DB.

## How to Run

```bash
source venv/bin/activate
uvicorn api.app:app --reload   # local dev, starts on port 8000
```

In production (Render), the configured start command is `python start.py` — a thin wrapper around `uvicorn api.app:app` with extra startup logging for debugging cold-start failures. Don't delete it; `render.yaml`'s start command is reference-only and isn't what the live dashboard service actually runs.

Frontend: `cd ../ai-rag-ui && npm run dev`

## Project Layout

8 independent layers with strict top-down dependencies:

```
api/          → FastAPI routes (incl. calendar + push), auth dependencies, schemas
auth/         → JWT, bcrypt, Google OAuth, Resend email (verification, reset, task reminders)
agent/        → LangGraph graph (route → execute_tool(s) → generate → extract_memory)
llm/          → factory.py picks Gemini, OpenRouter, Ollama, or Anthropic — per-user provider/model/API-key override
tools/        → 6 tools with BaseTool interface (rag, web, journal, task, memory, calendar)
memory/       → conversation history + long-term user facts + context builder
storage/      → plug-and-play DB: factory.py → backends/sqlite/ or backends/supabase/
rag/          → FAISS + BM25 hybrid search, embeddings, reranking, ingestion (consolidated)
```

## Key Patterns

- **Storage dispatchers**: `storage/repositories/*.py` are thin functions that delegate to `storage/factory.get_backend()`. Never put SQL in a repository file — put it in the backend implementation (`storage/backends/sqlite/` or `storage/backends/supabase/`).
- **Lazy ML imports**: `sentence_transformers`, `torch`, `faiss` are imported inside functions, never at module level. Cloud deployment (`requirements-cloud.txt`) doesn't have these — use `storage/backends/embedding_utils.safe_embed()` for any embedding call that must degrade gracefully.
- **LLM factory**: `llm/factory.get_llm_client(provider=None, model=None, api_key=None)` returns `GeminiClient`, `OpenRouterClient`, `OllamaClient`, or `AnthropicClient`. All four share the same interface: `.chat()`, `.chat_stream()`, `.generate()`, `.chat_full_async()`. Per-user overrides are read from `user["llm_provider"]` / `user["llm_model"]` plus an optional personal API key (`users.llm_api_key`, fetched only when `has_llm_api_key` is set; set via `PATCH /auth/llm-settings`, empty string clears it) and threaded through `AgentState` → every node that calls the LLM. Clients built with a user API key are not cached.
- **Multi-tool routing**: `agent/nodes.py::route()` makes a single LLM call that returns `{"tools": [{"tool": ..., "args": {...}}, ...]}` — supports calling multiple tools in one turn. Falls back to keyword matching (`_keyword_fallback_route`) if the LLM call fails.
- **Web search providers**: `tools/web_tool.py` dispatches to `tools/web_search/ddgs_search.py` (free, scraping-based) or `tools/web_search/tavily_search.py` (API key, faster/cleaner) based on `WEB_SEARCH_PROVIDER`.
- **Auth**: All data routes use `Depends(get_current_user)` from `api/dependencies.py`. `api/routes/auth.py` holds the public "get a token" flows (register, login, Google OAuth, password reset). `api/routes/profile.py` holds the authenticated "manage my account" flows (profile, password change, LLM settings) — both share the `/auth` URL prefix, split purely for file size. Shared rate-limiting (`auth/rate_limit.py`) and verification codes (`auth/verification.py`) live in the `auth/` package.
- **Config**: `configs/config.py` — Pydantic BaseSettings loading from `.env`. All settings have defaults so a missing `.env` never crashes startup.
- **Timeouts everywhere**: routing (15s), tool execution (20s), web search (15s hard ceiling) — all bounded so a slow external call (web search, LLM) can never hang a chat request indefinitely. See `agent/runner.py` and `tools/web_search/ddgs_search.py`.
- **Timezone**: the frontend sends the browser timezone in the chat payload; it flows through `AgentState` so the routing prompt's date context uses the user's local time (`agent/nodes.py`).
- **Recurring tasks/events**: `tasks` and `calendar_events` have a `recurrence` column (daily/weekly/monthly). Completing a recurring task spawns the next occurrence in the backend task repo (`_spawn_next_recurrence`) — the logic lives in each backend, so keep sqlite and supabase implementations in sync.
- **Web Push**: `api/routes/push.py` handles VAPID key exposure + subscribe/unsubscribe; `send_push_notification()` there is imported by `api/routes/tasks.py::send_reminders` (GET `/tasks/send-reminders`, also sends Resend emails via `auth/email.py::send_task_reminder_email`). Requires `VAPID_PRIVATE_KEY`/`VAPID_PUBLIC_KEY` (generate with `scripts/generate_vapid_keys.py`); degrades to no-op if unset.

## Adding a New Tool

1. Create `tools/my_tool.py` implementing `BaseTool` (see `tools/base.py`)
2. Add to `tools/registry.py`
3. Add its name + args schema to `ROUTER_PROMPT` in `llm/prompts.py`
4. Add keyword triggers in `agent/nodes.py::_keyword_fallback_route()`

## Adding a New Database Backend

1. Create `storage/backends/mydb/` with repo modules matching `storage/backends/base.py` (user, conversation, journal, task, memory, verification, calendar, push)
2. Create `__init__.py` with `create_backend() -> StorageBackend`
3. Add `elif` in `storage/factory.py`
4. Set `DB_BACKEND=mydb` in `.env`

## Adding a New LLM Provider

1. Create `llm/myprovider_client.py` with `.chat()`, `.chat_stream()`, `.generate()`, `.chat_full_async()` — same signatures as `llm/ollama_client.py`
2. Add an `elif` in `llm/factory.py::get_llm_client()`
3. Add config fields in `configs/config.py` (API key, default model)
4. Add to `llm/factory.py::AVAILABLE_MODELS` so it shows up in Settings UI

## Files NOT to Edit

- `storage/repositories/*.py` — auto-dispatchers, don't add logic here
- `storage/backends/base.py` — abstract contracts, change carefully
- `configs/config.py` — add fields, don't remove (breaks existing `.env` files)

## Testing

```bash
venv/bin/python -c "
from configs.config import settings
from storage.factory import get_backend
get_backend()
from api.app import app
print(f'{len(app.routes)} routes OK')
"
```

## Environment Variables

Critical ones: `LLM_PROVIDER` (gemini/openrouter/ollama/anthropic), `DB_BACKEND` (sqlite/supabase), `JWT_SECRET`, `GOOGLE_API_KEY` (if gemini), `OPENROUTER_API_KEY` (if openrouter), `ANTHROPIC_API_KEY` (if anthropic), `SUPABASE_URL` + `SUPABASE_KEY` (if supabase), `WEB_SEARCH_PROVIDER` (ddgs/tavily), `TAVILY_API_KEY` (if tavily), `CORS_ORIGINS`, `VAPID_PRIVATE_KEY` + `VAPID_PUBLIC_KEY` (for Web Push; optional). See `.env.example` for all.

## Schema Migrations

When adding columns to `users` or other tables, update **three places**:
1. `storage/database.py` (`_SCHEMA` — SQLite, used fresh on every deploy since data resets)
2. `storage/backends/supabase/schema.sql` (for fresh Supabase projects)
3. An `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` migration snippet for existing Supabase projects (idempotent, safe to re-run)
