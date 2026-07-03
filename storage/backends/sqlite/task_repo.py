from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from storage.database import get_connection


def create_task(user_id: str, title: str, description: str | None = None,
                due_date: str | None = None, priority: str = "medium",
                recurrence: str | None = None) -> dict:
    task_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO tasks (id, user_id, title, description, due_date, priority, recurrence, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, user_id, title, description, due_date, priority, recurrence, now),
        )
    return {"id": task_id, "user_id": user_id, "title": title, "description": description,
            "due_date": due_date, "status": "pending", "priority": priority,
            "recurrence": recurrence, "reminder_sent_at": None,
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

    completing = fields.get("status") == "done" and current.get("status") != "done"

    allowed = {"title", "description", "due_date", "status", "priority", "recurrence", "reminder_sent_at"}
    for key, val in fields.items():
        if key in allowed:
            current[key] = val

    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """UPDATE tasks SET title=?, description=?, due_date=?, status=?, priority=?,
               recurrence=?, reminder_sent_at=?, updated_at=? WHERE id=? AND user_id=?""",
            (current["title"], current["description"], current["due_date"],
             current["status"], current["priority"], current.get("recurrence"),
             current.get("reminder_sent_at"), now, task_id, user_id),
        )

    # Auto-spawn next instance for recurring tasks
    if completing and current.get("recurrence") and current.get("due_date"):
        _spawn_next_recurrence(user_id, current)

    return get_task(task_id, user_id)


def _spawn_next_recurrence(user_id: str, task: dict) -> None:
    try:
        due = date.fromisoformat(task["due_date"])
        recurrence = task["recurrence"]
        if recurrence == "daily":
            next_due = due + timedelta(days=1)
        elif recurrence == "weekly":
            next_due = due + timedelta(weeks=1)
        elif recurrence == "monthly":
            month = due.month + 1 if due.month < 12 else 1
            year = due.year if due.month < 12 else due.year + 1
            day = min(due.day, [31,28,31,30,31,30,31,31,30,31,30,31][month-1])
            next_due = due.replace(year=year, month=month, day=day)
        else:
            return
        create_task(user_id, task["title"], task["description"],
                    str(next_due), task["priority"], task["recurrence"])
    except Exception:
        pass  # don't fail the original update if recurrence fails


def delete_task(task_id: str, user_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id),
        )
    return cursor.rowcount > 0


def get_tasks_due_today(user_id: str | None = None) -> list[dict]:
    """Return pending/in_progress tasks due today (or overdue) that haven't had a reminder sent today."""
    today = date.today().isoformat()
    with get_connection() as conn:
        if user_id:
            rows = conn.execute(
                """SELECT t.*, u.email, u.name FROM tasks t
                   JOIN users u ON u.id = t.user_id
                   WHERE t.user_id = ? AND t.due_date <= ? AND t.status NOT IN ('done', 'cancelled')
                   AND (t.reminder_sent_at IS NULL OR t.reminder_sent_at < ?)""",
                (user_id, today, today),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT t.*, u.email, u.name FROM tasks t
                   JOIN users u ON u.id = t.user_id
                   WHERE t.due_date <= ? AND t.status NOT IN ('done', 'cancelled')
                   AND (t.reminder_sent_at IS NULL OR t.reminder_sent_at < ?)""",
                (today, today),
            ).fetchall()
    return [dict(r) for r in rows]


def mark_reminder_sent(task_id: str) -> None:
    today = date.today().isoformat()
    with get_connection() as conn:
        conn.execute("UPDATE tasks SET reminder_sent_at = ? WHERE id = ?", (today, task_id))
