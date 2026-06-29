import os
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from api.dependencies import get_current_user
from configs.config import settings

router = APIRouter()


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    allowed = {".pdf", ".txt", ".xlsx", ".csv"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {allowed}")

    size_limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    content = await file.read()
    if len(content) > size_limit:
        raise HTTPException(413, f"File too large (max {settings.MAX_UPLOAD_MB}MB)")

    os.makedirs(settings.DATA_DIR, exist_ok=True)
    file_path = os.path.join(settings.DATA_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        from ingestion.ingest_documents import ingest_documents
        ingest_documents(settings.DATA_DIR, settings.STORAGE_DIR)
    except ImportError:
        raise HTTPException(501, "Document ingestion not available in cloud deployment")
    except Exception as e:
        raise HTTPException(500, f"Ingestion failed: {e}")

    return {"status": "ok", "filename": file.filename, "size": len(content)}


@router.delete("/delete")
async def delete_document(source: str, user: dict = Depends(get_current_user)):
    try:
        from retrieval.vector_store import VectorStore
        store = VectorStore.load(settings.STORAGE_DIR)
        store.delete_by_source(source)
        store.save(settings.STORAGE_DIR)
        return {"status": "deleted", "source": source}
    except ImportError:
        raise HTTPException(501, "Document management not available in cloud deployment")
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {e}")
