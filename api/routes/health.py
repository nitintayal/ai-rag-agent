from fastapi import APIRouter

from llm.model_manager import get_status
from configs.config import settings

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/status")
def status():
    result = {
        "status": "ok",
        "llm_provider": settings.LLM_PROVIDER,
        "database": settings.DATABASE_PATH,
        "features": {
            "memory_extraction": settings.MEMORY_EXTRACTION_ENABLED,
            "hybrid_search": settings.ENABLE_HYBRID,
            "reranking": settings.ENABLE_RERANK,
        },
    }
    if settings.LLM_PROVIDER == "gemini":
        result["gemini_model"] = settings.GEMINI_MODEL
        result["gemini_key_set"] = bool(settings.GOOGLE_API_KEY)
    else:
        result["llm"] = get_status(settings.OLLAMA_BASE_URL, settings.OLLAMA_CHAT_MODEL)
    return result
