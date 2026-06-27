from fastapi import APIRouter

from llm.model_manager import get_status
from configs.config import settings

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/status")
def status():
    llm_status = get_status(settings.OLLAMA_BASE_URL, settings.OLLAMA_CHAT_MODEL)
    return {
        "status": "ok",
        "llm": llm_status,
        "embedding_model": settings.EMBEDDING_MODEL,
        "database": settings.DATABASE_PATH,
        "features": {
            "memory_extraction": settings.MEMORY_EXTRACTION_ENABLED,
            "hybrid_search": settings.ENABLE_HYBRID,
            "reranking": settings.ENABLE_RERANK,
        },
    }
