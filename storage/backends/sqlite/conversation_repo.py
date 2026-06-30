from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from storage.database import get_connection


def create_conversation(user_id: str, title: str | None = None, conversation_id: str | None = None) -> dict:
    cid = conversation_id or str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        existing = conn.execute("SELECT * FROM conversations WHERE id = ?", (cid,)).fetchone()
        if existing:
            return dict(existing)
        conn.execute(
            "INSERT INTO conversations (id, user_id, title, created_at) VALUES (?, ?, ?, ?)",
            (cid, user_id, title, now),
        )
    return {"id": cid, "user_id": user_id, "title": title, "created_at": now, "updated_at": None}


def get_conversation(conversation_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        return dict(row) if row else None


def list_conversations(user_id: str, limit: int = 20, offset: int = 0) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def add_message(conversation_id: str, role: str, content: str,
                tool_name: str | None = None, tool_result: str | None = None) -> dict:
    msg_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO messages (id, conversation_id, role, content, tool_name, tool_result, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (msg_id, conversation_id, role, content, tool_name, tool_result, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
    return {"id": msg_id, "conversation_id": conversation_id, "role": role,
            "content": content, "tool_name": tool_name, "tool_result": tool_result, "created_at": now}


def get_messages(conversation_id: str, limit: int = 20) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM messages WHERE conversation_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (conversation_id, limit),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


def delete_conversation(conversation_id: str) -> bool:
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        cursor = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    return cursor.rowcount > 0
