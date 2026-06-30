from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


def _hf_default_path(local_path: str, data_path: str) -> str:
    data_root = Path("/data")
    if data_root.exists():
        return str(data_root / data_path)
    return local_path


class Settings(BaseSettings):

    # =========================
    # LLM Provider: "gemini", "openrouter", or "ollama"
    # =========================
    LLM_PROVIDER: str = "ollama"
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # =========================
    # OpenRouter (when LLM_PROVIDER=openrouter)
    # =========================
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = "meta-llama/llama-3.3-70b-instruct:free"

    # =========================
    # Ollama (when LLM_PROVIDER=ollama)
    # =========================
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "qwen2.5:7b"
    OLLAMA_TIMEOUT: int = 120

    # =========================
    # Embeddings & Reranking
    # =========================
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # =========================
    # Retrieval
    # =========================
    TOP_K: int = 4
    RETRIEVAL_K: int = 20
    VECTOR_WEIGHT: float = 0.7
    BM25_WEIGHT: float = 0.3
    HYBRID_K: int = 10
    RERANK_K: int = 5
    MIN_HYBRID_SCORE: float = 0.0
    MIN_RERANK_SCORE: float = -9999.0
    ENABLE_RERANK: bool = True
    ENABLE_HYBRID: bool = True

    # =========================
    # Chunking
    # =========================
    CHUNK_SIZE: int = 400
    CHUNK_OVERLAP: int = 80

    # =========================
    # Web Search
    # =========================
    WEB_SEARCH_PROVIDER: str = "ddgs"  # "ddgs" (free, scraping) or "tavily" (API, needs key)
    WEB_SEARCH_MAX_RESULTS: int = 3
    TAVILY_API_KEY: Optional[str] = None

    # =========================
    # API
    # =========================
    API_PORT: int = 8000
    MAX_UPLOAD_MB: int = 15

    # =========================
    # Storage
    # =========================
    DB_BACKEND: str = "sqlite"  # "sqlite" or "supabase" (or "postgres", "mongodb" when implemented)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    DATA_DIR: str = _hf_default_path("data/files", "data/files")
    STORAGE_DIR: str = _hf_default_path("data/storage", "data/storage")
    DATABASE_PATH: str = _hf_default_path("data/db/assistant.db", "data/db/assistant.db")

    # =========================
    # Memory
    # =========================
    CONVERSATION_HISTORY_LIMIT: int = 20
    MEMORY_EXTRACTION_ENABLED: bool = True

    # =========================
    # Auth
    # =========================
    JWT_SECRET: str = "change-me-in-production"  # MUST override via env var in production
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    CORS_ORIGINS: str = "*"  # comma-separated
    RESEND_API_KEY: Optional[str] = None
    RESEND_FROM_EMAIL: str = "ai-personal-agent@resend.dev"
    FRONTEND_URL: str = "http://localhost:5173"
    REQUIRE_EMAIL_VERIFICATION: bool = False

    # =========================
    # Debug
    # =========================
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
