from datetime import datetime, timezone
from uuid import uuid4

from storage.database import get_connection


def create_event(user_id: str, title: str, start_time: str,
                 end_time: str | None = None, description: str | None = None) -> dict:
    eid = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO calendar_events (id, user_id, title, description, start_time, end_time, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (eid, user_id, title, description, start_time, end_time, now),
        )
    return {"id": eid, "user_id": user_id, "title": title, "description": description,
            "start_time": start_time, "end_time": end_time, "created_at": now}


def list_events(user_id: str, limit: int = 20) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM calendar_events WHERE user_id = ? ORDER BY start_time ASC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_event(event_id: str, user_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM calendar_events WHERE id = ? AND user_id = ?",
            (event_id, user_id),
        )
    return cursor.rowcount > 0
