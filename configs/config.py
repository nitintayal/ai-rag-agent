from pathlib import Path
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings


def _hf_default_path(local_path: str, data_path: str) -> str:
    data_root = Path("/data")
    if data_root.exists():
        return str(data_root / data_path)
    return local_path


class Settings(BaseSettings):

    # =========================
    # Models
    # =========================
    EMBEDDING_MODEL: str
    RERANK_MODEL: str
    LLM_MODEL: str
    ROUTER_PROVIDER: str
    ROUTER_MODEL: str
    GOOGLE_API_KEY: str
    WEB_SEARCH_MAX_RESULTS: int

    # =========================
    # Agent Runtime
    # =========================
    AGENT_MODE: str = "deep"
    DEEP_AGENT_MODEL: str
    DEEP_AGENT_RECURSION_LIMIT: int = 40
    DEEP_AGENT_LOG_CONVERSATIONS: bool = False
    DEEP_AGENT_LOG_PATH: str = _hf_default_path("deep_agent_conversations.log", "deep_agent_conversations.log")

    # =========================
    # Retrieval
    # =========================
    TOP_K: int
    RETRIEVAL_K: int
    VECTOR_WEIGHT: float
    BM25_WEIGHT: float
    HYBRID_K: int
    RERANK_K: int
    MIN_HYBRID_SCORE: float = 0.0
    MIN_RERANK_SCORE: float = -9999.0

    ENABLE_RERANK: bool
    ENABLE_HYBRID: bool

    # =========================
    # Chunking
    # =========================
    CHUNK_SIZE: int
    CHUNK_OVERLAP: int

    # =========================
    # API
    # =========================
    STREAM_DELAY: float
    API_PORT: int
    MAX_UPLOAD_MB: int = 15

    # =========================
    # Storage
    # =========================
    DATA_DIR: str = _hf_default_path("data", "data")
    STORAGE_DIR: str = _hf_default_path("storage", "storage")
    JOURNAL_BACKEND: str = "postgres"
    JOURNAL_DATABASE_URL: Optional[str] = None
    JOURNAL_SQLITE_PATH: str = _hf_default_path("journal_demo.db", "journal_demo.db")

    # =========================
    # Debug
    # =========================
    DEBUG: bool
    SHOW_RETRIEVED: bool
    SHOW_RERANKED: bool

    @model_validator(mode="after")
    def validate_journal_settings(self):
        backend = self.JOURNAL_BACKEND.strip().lower()
        if backend == "postgres" and not self.JOURNAL_DATABASE_URL:
            raise ValueError("JOURNAL_DATABASE_URL is required when JOURNAL_BACKEND=postgres")
        if self.AGENT_MODE.strip().lower() not in {"legacy", "deep"}:
            raise ValueError("AGENT_MODE must be either 'legacy' or 'deep'")
        return self

    class Config:
        env_file = ".env"
        extra = "ignore"   # ignore unknown vars


settings = Settings()
