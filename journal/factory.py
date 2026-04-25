from configs.config import settings
from journal.postgres_store import PostgresJournalStore
from journal.sqlite_store import SqliteJournalStore


def get_journal_store():
    backend = settings.JOURNAL_BACKEND.strip().lower()
    if backend == "sqlite":
        return SqliteJournalStore(settings.JOURNAL_SQLITE_PATH)
    return PostgresJournalStore(settings.JOURNAL_DATABASE_URL)
