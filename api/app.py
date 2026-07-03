"""FastAPI application — the main entry point for the AI personal assistant."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from configs.config import settings
from storage.factory import get_backend

from api.routes import health, auth, profile, chat, conversations, documents, journal, tasks, calendar, push


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info(f"Starting AI Personal Assistant...")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"DB Backend: {settings.DB_BACKEND}")
    if settings.JWT_SECRET == "change-me-in-production" or len(settings.JWT_SECRET) < 32:
        logger.critical("JWT_SECRET is too short or using the default — set a 32+ char secret in env vars or all auth will fail with 401")
    get_backend()
    logger.info("Storage backend initialized")
    yield


app = FastAPI(
    title="AI Personal Assistant",
    version="2.0.0",
    lifespan=lifespan,
)

cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(documents.router)
app.include_router(journal.router)
app.include_router(tasks.router)
app.include_router(calendar.router)
app.include_router(push.router)


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
