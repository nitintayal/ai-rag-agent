"""Supabase backend."""

from storage.backends.base import StorageBackend
from storage.backends.supabase import (
    user_repo, conversation_repo, journal_repo, task_repo, memory_repo
)


def create_backend() -> StorageBackend:
    from storage.backends.supabase.client import get_supabase
    get_supabase()  # verify connection
    return StorageBackend(
        user=user_repo,
        conversation=conversation_repo,
        journal=journal_repo,
        task=task_repo,
        memory=memory_repo,
    )
