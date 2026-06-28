from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from storage.database import get_connection


def ensure_user(user_id: str, name: str | None = None) -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row:
            return dict(row)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO users (id, name, created_at) VALUES (?, ?, ?)",
            (user_id, name or user_id, now),
        )
        return {"id": user_id, "name": name or user_id, "created_at": now}


def get_user(user_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
