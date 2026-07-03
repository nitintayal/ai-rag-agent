"""SQLite backend — wraps the existing sqlite repos as a StorageBackend."""

from storage.backends.base import StorageBackend
from storage.backends.sqlite import (
    user_repo, conversation_repo, journal_repo, task_repo, memory_repo, verification_repo, calendar_repo, push_repo
)


def create_backend() -> StorageBackend:
    from storage.database import init_db
    from configs.config import settings
    init_db(settings.DATABASE_PATH)
    return StorageBackend(
        user=user_repo,
        conversation=conversation_repo,
        journal=journal_repo,
        task=task_repo,
        memory=memory_repo,
        verification=verification_repo,
        calendar=calendar_repo,
        push=push_repo,
    )
