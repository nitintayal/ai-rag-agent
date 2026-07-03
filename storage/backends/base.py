"""Abstract base for all storage backends.

To add a new backend (MySQL, Postgres, Mongo, etc.):
1. Create a new folder: storage/backends/mydb/
2. Implement each repo module with the same function signatures below
3. Add your backend name to storage/factory.py
4. Set DB_BACKEND=mydb in .env
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional


class BaseUserRepo(ABC):
    @abstractmethod
    def ensure_user(self, user_id: str, name: str | None = None) -> dict: ...

    @abstractmethod
    def get_user(self, user_id: str) -> Optional[dict]: ...

    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[dict]: ...

    @abstractmethod
    def create_user(self, email: str, name: str, password: str | None = None,
                    auth_provider: str = "local", avatar_url: str | None = None) -> dict: ...

    @abstractmethod
    def update_user(self, user_id: str, **fields) -> Optional[dict]: ...


class BaseVerificationRepo(ABC):
    @abstractmethod
    def create_code(self, email: str, code: str, purpose: str, expires_at: str) -> dict: ...

    @abstractmethod
    def verify_and_consume(self, email: str, code: str, purpose: str) -> bool: ...

    @abstractmethod
    def invalidate_pending(self, email: str, purpose: str) -> None: ...


class BaseConversationRepo(ABC):
    @abstractmethod
    def create_conversation(self, user_id: str, title: str | None = None,
                            conversation_id: str | None = None) -> dict: ...

    @abstractmethod
    def get_conversation(self, conversation_id: str) -> Optional[dict]: ...

    @abstractmethod
    def list_conversations(self, user_id: str, limit: int = 20, offset: int = 0) -> list[dict]: ...

    @abstractmethod
    def add_message(self, conversation_id: str, role: str, content: str,
                    tool_name: str | None = None, tool_result: str | None = None) -> dict: ...

    @abstractmethod
    def get_messages(self, conversation_id: str, limit: int = 20) -> list[dict]: ...

    @abstractmethod
    def delete_conversation(self, conversation_id: str) -> bool: ...


class BaseJournalRepo(ABC):
    @abstractmethod
    def list_entries(self, user_id: str, limit: int = 20, offset: int = 0) -> dict: ...

    @abstractmethod
    def get_entry(self, entry_id: str, user_id: str) -> Optional[dict]: ...

    @abstractmethod
    def add_entry(self, user_id: str, content: str, title: str | None = None,
                  mood: str | None = None, tags: list[str] | None = None,
                  entry_date: date | str | None = None) -> dict: ...

    @abstractmethod
    def update_entry(self, entry_id: str, user_id: str, **fields) -> Optional[dict]: ...

    @abstractmethod
    def delete_entry(self, entry_id: str, user_id: str) -> bool: ...

    @abstractmethod
    def search_entries(self, user_id: str, query: str, k: int = 5) -> list[dict]: ...


class BaseTaskRepo(ABC):
    @abstractmethod
    def create_task(self, user_id: str, title: str, description: str | None = None,
                    due_date: str | None = None, priority: str = "medium") -> dict: ...

    @abstractmethod
    def list_tasks(self, user_id: str, status: str | None = None, limit: int = 50) -> list[dict]: ...

    @abstractmethod
    def get_task(self, task_id: str, user_id: str) -> Optional[dict]: ...

    @abstractmethod
    def update_task(self, task_id: str, user_id: str, **fields) -> Optional[dict]: ...

    @abstractmethod
    def delete_task(self, task_id: str, user_id: str) -> bool: ...


class BaseMemoryRepo(ABC):
    @abstractmethod
    def store_memory(self, user_id: str, key: str, value: str, category: str = "general",
                     embedding: list[float] | None = None) -> dict: ...

    @abstractmethod
    def get_memory(self, user_id: str, key: str) -> Optional[dict]: ...

    @abstractmethod
    def list_memories(self, user_id: str, category: str | None = None) -> list[dict]: ...

    @abstractmethod
    def search_memories(self, user_id: str, query_embedding: list[float], k: int = 5) -> list[dict]: ...

    @abstractmethod
    def delete_memory(self, user_id: str, key: str) -> bool: ...


class BaseCalendarRepo(ABC):
    @abstractmethod
    def create_event(self, user_id: str, title: str, start_time: str,
                     end_time: str | None = None, description: str | None = None) -> dict: ...

    @abstractmethod
    def list_events(self, user_id: str, limit: int = 20) -> list[dict]: ...

    @abstractmethod
    def delete_event(self, event_id: str, user_id: str) -> bool: ...


class StorageBackend:
    """Container for all repository implementations of a backend."""
    def __init__(self, user, conversation, journal, task, memory, verification=None, calendar=None, push=None):
        self.user = user
        self.conversation = conversation
        self.journal = journal
        self.task = task
        self.memory = memory
        self.verification = verification
        self.calendar = calendar
        self.push = push
