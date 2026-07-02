import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

_db_path: str | None = None


def init_db(path: str) -> None:
    global _db_path
    _db_path = path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(_SCHEMA)


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    if _db_path is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    email       TEXT UNIQUE,
    password    TEXT,
    avatar_url  TEXT,
    auth_provider TEXT NOT NULL DEFAULT 'local',
    email_verified INTEGER NOT NULL DEFAULT 0,
    llm_provider TEXT,
    llm_model   TEXT,
    llm_api_key TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id),
    title       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_conversations_user
    ON conversations(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system', 'tool')),
    content         TEXT NOT NULL,
    tool_name       TEXT,
    tool_result     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages(conversation_id, created_at);

CREATE TABLE IF NOT EXISTS journal_entries (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    title       TEXT,
    content     TEXT NOT NULL,
    mood        TEXT,
    tags        TEXT NOT NULL DEFAULT '[]',
    entry_date  TEXT NOT NULL,
    embedding   TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_journal_user
    ON journal_entries(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    title       TEXT NOT NULL,
    description TEXT,
    due_date    TEXT,
    status      TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'done', 'cancelled')),
    priority    TEXT NOT NULL DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_user
    ON tasks(user_id, status, due_date);

CREATE TABLE IF NOT EXISTS user_memories (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'general',
    embedding   TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT,
    UNIQUE(user_id, key)
);
CREATE INDEX IF NOT EXISTS idx_memories_user
    ON user_memories(user_id);

CREATE TABLE IF NOT EXISTS verification_codes (
    id          TEXT PRIMARY KEY,
    email       TEXT NOT NULL,
    code        TEXT NOT NULL,
    purpose     TEXT NOT NULL CHECK(purpose IN ('email_verify', 'password_reset')),
    expires_at  TEXT NOT NULL,
    used        INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_verification_email
    ON verification_codes(email, purpose, used);

CREATE TABLE IF NOT EXISTS calendar_events (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    title       TEXT NOT NULL,
    description TEXT,
    start_time  TEXT NOT NULL,
    end_time    TEXT,
    all_day     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_calendar_user
    ON calendar_events(user_id, start_time);
"""
