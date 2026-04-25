# AI RAG Agent

Agentic RAG system built with FastAPI, LangGraph, hybrid retrieval, local Hugging Face generation, optional structured-output routing, and a PostgreSQL-backed journal memory API.

## What It Does

- Answers questions from your local knowledge base with hybrid retrieval.
- Routes time-sensitive or external queries to web search.
- Streams answers and source lists from the `/ask` endpoint.
- Supports document upload, ingestion, and deletion.
- Stores personal journal entries in PostgreSQL and supports semantic journal search.
- Includes a parallel Gradio chat app for Hugging Face Spaces demos.

## Core Features

- LangGraph agent with `decide -> rag|web -> generate`
- Hybrid search using FAISS + BM25
- Cross-encoder reranking
- Local answer generation with Hugging Face models
- Optional structured router using Gemini JSON/schema output
- Web search with source URL capture
- Journal CRUD + semantic search
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
│   ├── schemas.py
│   └── store.py
├── retrieval/
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
JOURNAL_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/journal_db
```

Notes:

- Use `ROUTER_PROVIDER=local` to keep routing fully local.
- Use `ROUTER_PROVIDER=gemini` to enable schema-constrained routing with Gemini.
- `GOOGLE_API_KEY` is required only for the Gemini router path.

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

List entries for a user.

`GET /journal/entries/{entry_id}?user_id=user-1`

Fetch a single entry.

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
