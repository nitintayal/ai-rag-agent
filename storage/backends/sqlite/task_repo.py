from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from storage.database import get_connection


def create_task(user_id: str, title: str, description: str | None = None,
                due_date: str | None = None, priority: str = "medium") -> dict:
    task_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO tasks (id, user_id, title, description, due_date, priority, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (task_id, user_id, title, description, due_date, priority, now),
        )
    return {"id": task_id, "user_id": user_id, "title": title, "description": description,
            "due_date": due_date, "status": "pending", "priority": priority,
            "created_at": now, "updated_at": None}


def list_tasks(user_id: str, status: str | None = None, limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY due_date ASC NULLS LAST, created_at DESC LIMIT ?",
                (user_id, status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE user_id = ? ORDER BY due_date ASC NULLS LAST, created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
    return [dict(r) for r in rows]


def get_task(task_id: str, user_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def update_task(task_id: str, user_id: str, **fields) -> Optional[dict]:
    current = get_task(task_id, user_id)
    if not current:
        return None

    for key, val in fields.items():
        if val is not None:
            current[key] = val

    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """UPDATE tasks SET title=?, description=?, due_date=?, status=?, priority=?, updated_at=?
               WHERE id=? AND user_id=?""",
            (current["title"], current["description"], current["due_date"],
             current["status"], current["priority"], now, task_id, user_id),
        )
    return get_task(task_id, user_id)


def delete_task(task_id: str, user_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id),
        )
    return cursor.rowcount > 0
