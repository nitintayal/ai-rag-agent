from pydantic_settings import BaseSettings


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
    # Retrieval
    # =========================
    TOP_K: int
    RETRIEVAL_K: int
    VECTOR_WEIGHT: float
    BM25_WEIGHT: float
    HYBRID_K: int
    RERANK_K: int

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

    # =========================
    # Storage
    # =========================
    DATA_DIR: str
    STORAGE_DIR: str
    JOURNAL_DATABASE_URL: str

    # =========================
    # Debug
    # =========================
    DEBUG: bool
    SHOW_RETRIEVED: bool
    SHOW_RERANKED: bool

    class Config:
        env_file = ".env"
        extra = "ignore"   # ignore unknown vars


settings = Settings()
