import sys
from datetime import date
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

mcp = FastMCP("journal")


def _json_safe(value: Any):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _parse_entry_date(entry_date: str | None):
    if not entry_date:
        return None
    return date.fromisoformat(entry_date)


@mcp.tool()
def create_journal_entry(
    user_id: str,
    content: str,
    title: str | None = None,
    mood: str | None = None,
    tags: list[str] | None = None,
    entry_date: str | None = None,
):
    """Create a journal entry for a user."""
    from journal.factory import get_journal_store
    from journal.schemas import JournalEntryCreate

    store = get_journal_store()
    entry = store.add_entry(
        JournalEntryCreate(
            user_id=user_id,
            content=content,
            title=title,
            mood=mood,
            tags=tags or [],
            entry_date=_parse_entry_date(entry_date),
        )
    )
    return _json_safe(entry)


@mcp.tool()
def list_journal_entries(user_id: str, limit: int = 20, offset: int = 0):
    """List journal entries for a user."""
    from journal.factory import get_journal_store

    store = get_journal_store()
    return _json_safe(store.list_entries(user_id=user_id, limit=limit, offset=offset))


@mcp.tool()
def get_journal_entry(entry_id: str, user_id: str):
    """Fetch one journal entry by id for a user."""
    from journal.factory import get_journal_store

    store = get_journal_store()
    return _json_safe(store.get_entry(entry_id=entry_id, user_id=user_id))


@mcp.tool()
def update_journal_entry(
    entry_id: str,
    user_id: str,
    title: str | None = None,
    content: str | None = None,
    mood: str | None = None,
    tags: list[str] | None = None,
    entry_date: str | None = None,
):
    """Update an existing journal entry."""
    from journal.factory import get_journal_store
    from journal.schemas import JournalEntryUpdate

    store = get_journal_store()
    payload = JournalEntryUpdate(
        title=title,
        content=content,
        mood=mood,
        tags=tags,
        entry_date=_parse_entry_date(entry_date),
    )
    entry = store.update_entry(entry_id=entry_id, user_id=user_id, payload=payload)
    return _json_safe(entry)


@mcp.tool()
def delete_journal_entry(entry_id: str, user_id: str):
    """Delete a journal entry by id for a user."""
    from journal.factory import get_journal_store

    store = get_journal_store()
    return {"deleted": store.delete_entry(entry_id=entry_id, user_id=user_id)}


@mcp.tool()
def search_journal_entries(user_id: str, query: str, k: int = 5):
    """Semantic search across a user's journal entries."""
    from journal.factory import get_journal_store

    store = get_journal_store()
    return _json_safe(store.search_entries(user_id=user_id, query=query, k=k))


if __name__ == "__main__":
    mcp.run()
