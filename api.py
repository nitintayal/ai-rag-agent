import re

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from configs.config import settings
from embeddings.sentence_embeddings import embed_query
from retrieval.vector_store import VectorStore
from agent.local_llm_answer import answer_with_llm
from agent.agent_executor import run_agent
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio
from fastapi import UploadFile, File
from pathlib import Path
from ingestion.ingest_documents import ingest_documents
import json
from journal.schemas import (
    JournalEntryCreate,
    JournalEntriesPage,
    JournalEntryResponse,
    JournalEntryUpdate,
    JournalSearchRequest,
    JournalSearchResult,
)
from journal.factory import get_journal_store

DATA_FOLDER = Path(settings.DATA_DIR)
SUPPORTED_UPLOAD_EXTENSIONS = {".txt", ".pdf", ".xlsx"}
MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_MB * 1024 * 1024

app = FastAPI(title="Local RAG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_safe_vector_store():
    try:
        return VectorStore.load(settings.STORAGE_DIR)
    except Exception as exc:
        print(f"Vector store unavailable: {exc}")
        return None


def get_safe_journal_store():
    try:
        return get_journal_store()
    except Exception as exc:
        print(f"Journal store unavailable: {exc}")
        return None


def sanitize_filename(filename: str) -> str:
    name = Path(filename or "").name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    if not name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    return name


def get_upload_destination(filename: str) -> Path:
    safe_name = sanitize_filename(filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in SUPPORTED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    DATA_FOLDER.mkdir(parents=True, exist_ok=True)
    destination = DATA_FOLDER / safe_name
    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    for counter in range(1, 1000):
        candidate = DATA_FOLDER / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
    raise HTTPException(status_code=409, detail="Could not create a unique filename")


def vector_store_status():
    store = get_safe_vector_store()
    if store is None:
        return {"available": False, "documents": 0}
    return {
        "available": True,
        "documents": len(store.documents),
        "storage_dir": settings.STORAGE_DIR,
    }


def journal_status():
    journal_store = get_safe_journal_store()
    return {
        "available": journal_store is not None,
        "backend": settings.JOURNAL_BACKEND,
    }


class QuestionRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status")
def status():
    return {
        "vector_store": vector_store_status(),
        "journal": journal_status(),
        "web_search": {"enabled": True, "max_results": settings.WEB_SEARCH_MAX_RESULTS},
        "models": {
            "embedding": settings.EMBEDDING_MODEL,
            "rerank": settings.RERANK_MODEL,
            "llm": settings.LLM_MODEL,
            "router_provider": settings.ROUTER_PROVIDER,
        },
    }


@app.post("/ask-old")
def ask_question(req: QuestionRequest):
    question = req.question
    store = get_safe_vector_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Vector store is not available. Ingest documents first.")

    query_vector = embed_query(question)
    results = store.search(query_vector, k=3)
    if not results:
        return {
            "question": question,
            "answer": "No knowledge base results were found. Upload or ingest documents first.",
            "confidence": 0,
            "sources": [],
        }
    print("Search results:", results)
    context = "\n\n".join(
        f"[Source: {r['document']['source']}]\n{r['document']['content']}"
        for r in results
    )

    answer = answer_with_llm(question, context)

    sources = sorted(set(str(r["document"]["source"]) for r in results))
    avg_confidence = sum(r["score"] for r in results) / len(results)

    return {
        "question": question,
        "answer": answer,
        "confidence": round(avg_confidence * 100, 2),
        "sources": sources
    }

@app.post("/ask")
async def ask_question(req: QuestionRequest):

    async def generate():

        result = await asyncio.to_thread(run_agent, req.question)

        for word in result["answer"].split():
            yield word + " "
            await asyncio.sleep(settings.STREAM_DELAY)
        
        sources = result.get("sources") or []

        yield "\n\n SOURCES :\n"
        yield json.dumps(sources)

    return StreamingResponse(generate(), media_type="text/plain")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):

    file_path = get_upload_destination(file.filename)
    bytes_written = 0

    with open(file_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_BYTES:
                buffer.close()
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File is too large. Limit is {settings.MAX_UPLOAD_MB} MB.",
                )
            buffer.write(chunk)
    
    result = ingest_documents(file_path)

    return {
        "message": f"{file_path.name} uploaded and ingested successfully",
        "filename": file_path.name,
        "bytes": bytes_written,
        "ingestion": result,
    }

@app.delete("/delete")
def delete_file(source: str):

    store = get_safe_vector_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Vector store is not available")

    store.delete_by_source(source)

    store.save(settings.STORAGE_DIR)

    file_path = DATA_FOLDER / source

    if file_path.exists():
        file_path.unlink()

    return {"message": f"{source} removed successfully"}


@app.post("/journal/entries", response_model=JournalEntryResponse)
def create_journal_entry(
    payload: JournalEntryCreate,
    entry_id: str | None = Query(default=None),
):
    journal_store = get_safe_journal_store()
    if journal_store is None:
        raise HTTPException(status_code=503, detail="Journal store is not available")

    if entry_id:
        entry = journal_store.update_entry(
            entry_id=entry_id,
            user_id=payload.user_id,
            payload=JournalEntryUpdate(
                title=payload.title,
                content=payload.content,
                mood=payload.mood,
                tags=payload.tags,
                entry_date=payload.entry_date,
            ),
        )
        if entry is None:
            raise HTTPException(status_code=404, detail="Journal entry not found")
        return entry

    entry = journal_store.add_entry(payload)
    return entry


@app.get("/journal/entries", response_model=JournalEntriesPage)
def list_journal_entries(
    user_id: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    journal_store = get_safe_journal_store()
    if journal_store is None:
        raise HTTPException(status_code=503, detail="Journal store is not available")
    return journal_store.list_entries(user_id=user_id, limit=limit, offset=offset)


@app.get("/journal/entries/{entry_id}", response_model=JournalEntryResponse)
def get_journal_entry(entry_id: str, user_id: str = Query(..., min_length=1)):
    journal_store = get_safe_journal_store()
    if journal_store is None:
        raise HTTPException(status_code=503, detail="Journal store is not available")
    entry = journal_store.get_entry(entry_id=entry_id, user_id=user_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return entry


@app.patch("/journal/entries/{entry_id}", response_model=JournalEntryResponse)
def update_journal_entry(
    entry_id: str,
    payload: JournalEntryUpdate,
    user_id: str = Query(..., min_length=1),
):
    journal_store = get_safe_journal_store()
    if journal_store is None:
        raise HTTPException(status_code=503, detail="Journal store is not available")
    entry = journal_store.update_entry(
        entry_id=entry_id,
        user_id=user_id,
        payload=payload,
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return entry


@app.delete("/journal/entries/{entry_id}")
def delete_journal_entry(entry_id: str, user_id: str = Query(..., min_length=1)):
    journal_store = get_safe_journal_store()
    if journal_store is None:
        raise HTTPException(status_code=503, detail="Journal store is not available")
    deleted = journal_store.delete_entry(entry_id=entry_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    return {"message": f"Journal entry {entry_id} removed successfully"}


@app.post("/journal/search", response_model=list[JournalSearchResult])
def search_journal_entries(payload: JournalSearchRequest):
    journal_store = get_safe_journal_store()
    if journal_store is None:
        raise HTTPException(status_code=503, detail="Journal store is not available")
    results = journal_store.search_entries(
        user_id=payload.user_id,
        query=payload.query,
        k=payload.k,
    )
    return results
