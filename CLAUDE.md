# CLAUDE.md — AI Agent Context

This file helps AI coding agents (Claude Code, Copilot, etc.) understand the project.

## What This Is

An AI personal assistant with chat, RAG, web search, tasks, journal, memory, and calendar. FastAPI backend + React frontend. Deployed on Render (backend) + Vercel (frontend).

## How to Run

```bash
source venv/bin/activate
python -m api.app           # starts on port 8000
```

Frontend: `cd ../ai-rag-ui && npm run dev`

## Project Layout

8 independent layers with strict top-down dependencies:

```
api/          → FastAPI routes, auth dependencies, schemas
auth/         → JWT, bcrypt, Google OAuth, Resend email
agent/        → LangGraph graph (route → execute → generate → extract_memory)
llm/          → factory.py picks Gemini or Ollama based on LLM_PROVIDER
tools/        → 6 tools with BaseTool interface (rag, web, journal, task, memory, calendar)
memory/       → conversation history + long-term user facts + context builder
storage/      → plug-and-play DB: factory.py → backends/sqlite/ or backends/supabase/
retrieval/    → FAISS + BM25 hybrid search (local only, not on cloud)
```

## Key Patterns

- **Storage dispatchers**: `storage/repositories/*.py` are thin functions that delegate to `storage/factory.get_backend()`. Never put SQL in a repository file — put it in the backend implementation.
- **Lazy ML imports**: `sentence_transformers`, `torch`, `faiss` are imported inside functions, never at module level. Cloud deployment doesn't have these — use `storage/backends/embedding_utils.safe_embed()`.
- **LLM factory**: `llm/factory.get_llm_client()` returns either `GeminiClient` or `OllamaClient`. Both have the same interface: `.chat()`, `.chat_stream()`, `.generate()`.
- **Auth**: All data routes use `Depends(get_current_user)` from `api/dependencies.py`. Auth routes (`/auth/*`) are public.
- **Config**: `configs/config.py` — Pydantic BaseSettings loading from `.env`. All settings have defaults.

## Adding a New Tool

1. Create `tools/my_tool.py` implementing `BaseTool`
2. Add to `tools/registry.py`
3. Add its name + args schema to the router prompt in `llm/prompts.py`
4. Add keyword triggers in `agent/nodes.py._keyword_fallback_route()`

## Adding a New Database Backend

1. Create `storage/backends/mydb/` with 5 repo modules matching `storage/backends/base.py`
2. Create `__init__.py` with `create_backend() -> StorageBackend`
3. Add `elif` in `storage/factory.py`
4. Set `DB_BACKEND=mydb` in `.env`

## Files NOT to Edit

- `storage/repositories/*.py` — auto-dispatchers, don't add logic here
- `storage/backends/base.py` — abstract contracts, change carefully
- `configs/config.py` — add fields, don't remove (breaks existing .env files)

## Testing

```bash
venv/bin/python -c "
from configs.config import settings
from storage.factory import get_backend
get_backend()
from api.app import app
print('OK')
"
```

## Environment Variables

Critical ones: `LLM_PROVIDER`, `DB_BACKEND`, `JWT_SECRET`, `GOOGLE_API_KEY` (if gemini), `SUPABASE_URL` + `SUPABASE_KEY` (if supabase). See `.env.example` for all.
