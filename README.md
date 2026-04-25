---
title: AI RAG Agent Demo
emoji: 💬
colorFrom: yellow
colorTo: blue
sdk: gradio
sdk_version: 6.13.0
app_file: app.py
pinned: false
---

# AI RAG Agent

Agentic RAG system built with FastAPI, LangGraph, hybrid retrieval, local Hugging Face generation, optional structured-output routing, and a journal memory layer that can run on PostgreSQL or SQLite depending on environment.

## What It Does

- Answers questions from your local knowledge base with hybrid retrieval.
- Routes time-sensitive or external queries to web search.
- Streams answers and source lists from the `/ask` endpoint.
- Supports document upload, ingestion, and deletion.
- Stores personal journal entries with pluggable backends:
  - PostgreSQL for the product/backend deployment
  - SQLite for demo/Hugging Face deployment
- Includes a parallel Gradio chat app for Hugging Face Spaces demos.

## Core Features

- LangGraph agent with `decide -> rag|web -> generate`
- Hybrid search using FAISS + BM25
- Cross-encoder reranking
- Local answer generation with Hugging Face models
- Optional structured router using Gemini JSON/schema output
- Web search with source URL capture
- Journal CRUD + semantic search
- Parallel deployment paths for FastAPI and Gradio
- Docker Compose setup with API + Postgres

## Architecture

```text
User Question
  -> FastAPI
  -> LangGraph Agent
     -> Decide Tool
        -> RAG Tool
        -> Web Tool
  -> Answer Generation
  -> Streamed Answer + Sources
```

## Request Flow

### RAG path

1. Query is embedded.
2. Hybrid retrieval runs across vector + BM25 search.
3. Results are reranked.
4. Top documents become context.
5. Local LLM generates the grounded answer.

### Web path

1. Router selects `web`.
2. DDGS fetches search results.
3. Titles, URLs, and snippets are converted into context.
4. The answer model responds using that web context.
5. Source URLs are streamed back as a normal serialized list.

## Project Structure

```text
ai-rag-agent/
├── agent/
│   ├── agent_executor.py
│   ├── agent_graph.py
│   ├── agent_state.py
│   ├── local_llm_answer.py
│   ├── rag_tool.py
│   ├── router.py
│   └── web_tool.py
├── configs/
│   └── config.py
├── embeddings/
├── ingestion/
├── journal/
│   ├── factory.py
│   ├── postgres_store.py
│   ├── schemas.py
│   ├── sqlite_store.py
│   └── store.py
├── retrieval/
├── app.py
├── api.py
├── docker-compose.yml
├── main.py
└── requirements.txt
```

## Setup

### 1. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Create `.env` from `.env.example` and set the required values.

Key variables:

```env
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
LLM_MODEL=Qwen/Qwen2-1.5B-Instruct

ROUTER_PROVIDER=local
ROUTER_MODEL=gemini-2.5-flash-lite
GOOGLE_API_KEY=
WEB_SEARCH_MAX_RESULTS=3

DATA_DIR=data
STORAGE_DIR=storage
JOURNAL_BACKEND=postgres
JOURNAL_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/journal_db
JOURNAL_SQLITE_PATH=journal_demo.db
```

Notes:

- Use `ROUTER_PROVIDER=local` to keep routing fully local.
- Use `ROUTER_PROVIDER=gemini` to enable schema-constrained routing with Gemini.
- `GOOGLE_API_KEY` is required only for the Gemini router path.
- Use `JOURNAL_BACKEND=postgres` for the product/backend deployment.
- Use `JOURNAL_BACKEND=sqlite` for demo deployments such as Hugging Face Spaces.
- When `/data` exists, storage defaults automatically point there for the demo.

### 4. Ingest documents

```bash
python3 main.py
```

### 5. Run the API

```bash
uvicorn api:app --reload --port 8000
```

Open docs at [http://localhost:8000/docs](http://localhost:8000/docs).

### 6. Run the Gradio demo

```bash
python3 app.py
```

This launches a ChatGPT-style Gradio UI that runs in parallel with the existing FastAPI backend path.

## Journal Backends

The journal layer supports two storage modes behind the same API:

- `postgres`: product/default backend
- `sqlite`: demo backend

### Product mode

```env
JOURNAL_BACKEND=postgres
JOURNAL_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/journal_db
```

### Demo mode

```env
JOURNAL_BACKEND=sqlite
JOURNAL_SQLITE_PATH=journal_demo.db
```

For Hugging Face Spaces, use persistent storage and point SQLite at `/data`:

```env
JOURNAL_BACKEND=sqlite
JOURNAL_SQLITE_PATH=/data/journal_demo.db
```

You can start from [.env.hf.example] for a Space-friendly configuration.

## Docker

Run the API and PostgreSQL together:

```bash
docker compose up --build
```

Services:

- `rag-api` on port `8000`
- `postgres` on port `5432`

## Deployment Modes

- `api.py`: backend/API entrypoint for product integrations such as a future Vercel frontend
- `app.py`: Gradio demo entrypoint for Hugging Face Spaces

For Hugging Face Spaces, keep `app.py` at the repo root and install dependencies from `requirements.txt`.

Recommended deployment split:

- Product stack: FastAPI + PostgreSQL
- Demo stack: Gradio + SQLite

### Hugging Face Spaces

Recommended config for the demo:

```env
JOURNAL_BACKEND=sqlite
JOURNAL_SQLITE_PATH=/data/journal_demo.db
```

Notes:

- `app.py` is the Space entrypoint.
- Attach persistent storage if you want uploaded files, vector indexes, and journal data to survive restarts.
- SQLite is recommended for Spaces because a normal external PostgreSQL service on port `5432` is not the simplest deployment path there.
- `DATA_DIR`, `STORAGE_DIR`, and `JOURNAL_SQLITE_PATH` now default to `/data/...` automatically when that mount exists.

### Hugging Face Deployment Steps

1. Create a new Hugging Face Space and choose `Gradio`.
2. Push this repository to the Space.
3. In the Space settings, add variables from [.env.hf.example].
4. Attach persistent storage so `/data` survives restarts.
5. Launch the Space with `app.py` as the entrypoint.

## API Endpoints

### Ask

`POST /ask`

Request:

```json
{
  "question": "What changed in the latest policy?"
}
```

Response format:

- streamed answer text
- trailing `SOURCES :`
- serialized source list, for example:

```text
SOURCES :
["https://example.com/news","employee_policy.pdf"]
```

### Legacy Ask

`POST /ask-old`

Returns a non-streaming RAG-only response with confidence and sources.

### Upload

`POST /upload`

Uploads a document and ingests it into the knowledge base.

### Delete Document

`DELETE /delete?source=<filename>`

Removes a source from storage and deletes the local file.

### Journal APIs

`POST /journal/entries`

Create a journal entry.

```json
{
  "user_id": "user-1",
  "title": "Good day",
  "content": "Finished a project milestone.",
  "mood": "happy",
  "tags": ["work", "progress"]
}
```

`GET /journal/entries?user_id=user-1`

List entries for a user with pagination metadata.

Response shape:

```json
{
  "items": [],
  "total": 0,
  "limit": 20,
  "offset": 0,
  "has_more": false
}
```

`GET /journal/entries/{entry_id}?user_id=user-1`

Fetch a single entry.

`PATCH /journal/entries/{entry_id}?user_id=user-1`

Update an existing journal entry. This preserves `created_at` and writes `updated_at`.

`DELETE /journal/entries/{entry_id}?user_id=user-1`

Delete a journal entry.

`POST /journal/search`

Semantic search across a user's journal entries.

```json
{
  "user_id": "user-1",
  "query": "times I felt productive",
  "k": 5
}
```

### Journal timestamp behavior

- `created_at` is set once when a journal entry is created.
- `updated_at` stays empty until the entry is edited.
- Proper edits should use `PATCH /journal/entries/{entry_id}`.
- For backward compatibility, `POST /journal/entries?entry_id=...` also updates an existing entry if an `entry_id` is supplied.

## Routing Modes

### Local router

Uses the local LLM prompt plus a keyword fallback.

### Structured router

Uses Gemini with a schema that constrains output to:

```json
{"tool": "web"}
```

or

```json
{"tool": "rag"}
```

This makes the route decision easier to validate and safer to parse than free-form text.

## Current Additions In This Version

- Structured tool routing with schema-constrained output
- Env-configurable router and web search parameters
- Web search sources carried through the agent response
- Streamed sources returned as a serialized list for UI parsing
- PostgreSQL-backed journal memory endpoints
- Docker Compose setup for API + Postgres

## Development Notes

- `python3 -m compileall agent configs api.py` is a quick syntax sanity check.
- If you use the Gemini router, make sure `google-genai` is installed from `requirements.txt`.
- If web search fails, confirm the environment running the app has `ddgs` installed.
