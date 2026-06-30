from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from storage.database import get_connection


def ensure_user(user_id: str, name: str | None = None) -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row:
            return _serialize(row)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO users (id, name, created_at) VALUES (?, ?, ?)",
            (user_id, name or user_id, now),
        )
        return {"id": user_id, "name": name or user_id, "created_at": now}


def get_user(user_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _serialize(row) if row else None


def get_user_by_email(email: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return _serialize(row) if row else None


def get_user_by_email_with_password(email: str) -> Optional[dict]:
    """Internal use only — includes the password hash. Never expose via API."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def create_user(email: str, name: str, password: str | None = None,
                auth_provider: str = "local", avatar_url: str | None = None) -> dict:
    user_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO users (id, name, email, password, avatar_url, auth_provider, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, name, email, password, avatar_url, auth_provider, now),
        )
    return {"id": user_id, "name": name, "email": email, "avatar_url": avatar_url,
            "auth_provider": auth_provider, "created_at": now}


def update_user(user_id: str, **fields) -> Optional[dict]:
    allowed = {"name", "password", "avatar_url", "email_verified", "llm_provider", "llm_model"}
    set_clauses = []
    values = []
    for key, val in fields.items():
        if key in allowed:
            set_clauses.append(f"{key} = ?")
            values.append(val)
    if not set_clauses:
        return get_user(user_id)
    values.append(user_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?", values)
    return get_user(user_id)


def _serialize(row) -> dict:
    d = dict(row)
    d.pop("password", None)
    return d
