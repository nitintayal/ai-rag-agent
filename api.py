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
import shutil
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

app = FastAPI(title="Local RAG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Load vector store once at startup
store = VectorStore.load(settings.STORAGE_DIR)
journal_store = get_journal_store()

class QuestionRequest(BaseModel):
    question: str


@app.post("/ask-old")
def ask_question(req: QuestionRequest):
    question = req.question
    query_vector = embed_query(question)
    results = store.search(query_vector, k=3)
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

    file_path = DATA_FOLDER / file.filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    ingest_documents(file_path)

    return {"message": f"{file.filename} uploaded successfully"}

@app.delete("/delete")
def delete_file(source: str):

    store = VectorStore.load(settings.STORAGE_DIR)

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
    return journal_store.list_entries(user_id=user_id, limit=limit, offset=offset)


@app.get("/journal/entries/{entry_id}", response_model=JournalEntryResponse)
def get_journal_entry(entry_id: str, user_id: str = Query(..., min_length=1)):
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
    deleted = journal_store.delete_entry(entry_id=entry_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    return {"message": f"Journal entry {entry_id} removed successfully"}


@app.post("/journal/search", response_model=list[JournalSearchResult])
def search_journal_entries(payload: JournalSearchRequest):
    results = journal_store.search_entries(
        user_id=payload.user_id,
        query=payload.query,
        k=payload.k,
    )
    return results
