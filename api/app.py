"""FastAPI application — the main entry point for the AI personal assistant."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from configs.config import settings
from storage.database import init_db

from api.routes import health, chat, documents, journal, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info(f"Starting AI Personal Assistant...")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Database: {settings.DATABASE_PATH}")
    init_db(settings.DATABASE_PATH)
    logger.info("Database initialized")
    yield


app = FastAPI(
    title="AI Personal Assistant",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(journal.router)
app.include_router(tasks.router)


def start():
    import uvicorn
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    start()
