from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from storage.database import get_connection


def create_event(user_id: str, title: str, start_time: str,
                 end_time: str | None = None, description: str | None = None,
                 location: str | None = None, all_day: bool = False,
                 recurrence: str | None = None) -> dict:
    eid = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO calendar_events
               (id, user_id, title, description, start_time, end_time, all_day, location, recurrence, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (eid, user_id, title, description, start_time, end_time,
             1 if all_day else 0, location, recurrence, now),
        )
    return {"id": eid, "user_id": user_id, "title": title, "description": description,
            "start_time": start_time, "end_time": end_time, "all_day": all_day,
            "location": location, "recurrence": recurrence, "created_at": now, "updated_at": None}


def get_event(event_id: str, user_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM calendar_events WHERE id = ? AND user_id = ?", (event_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def list_events(user_id: str, limit: int = 50,
                start: str | None = None, end: str | None = None) -> list[dict]:
    with get_connection() as conn:
        if start and end:
            rows = conn.execute(
                """SELECT * FROM calendar_events WHERE user_id = ?
                   AND start_time >= ? AND start_time <= ?
                   ORDER BY start_time ASC LIMIT ?""",
                (user_id, start, end, limit),
            ).fetchall()
        elif start:
            rows = conn.execute(
                "SELECT * FROM calendar_events WHERE user_id = ? AND start_time >= ? ORDER BY start_time ASC LIMIT ?",
                (user_id, start, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM calendar_events WHERE user_id = ? ORDER BY start_time ASC LIMIT ?",
                (user_id, limit),
            ).fetchall()
    return [dict(r) for r in rows]


def update_event(event_id: str, user_id: str, **fields) -> Optional[dict]:
    current = get_event(event_id, user_id)
    if not current:
        return None
    allowed = {"title", "description", "start_time", "end_time", "all_day", "location", "recurrence"}
    for key, val in fields.items():
        if key in allowed:
            current[key] = val
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """UPDATE calendar_events SET title=?, description=?, start_time=?, end_time=?,
               all_day=?, location=?, recurrence=?, updated_at=? WHERE id=? AND user_id=?""",
            (current["title"], current["description"], current["start_time"], current["end_time"],
             1 if current.get("all_day") else 0, current.get("location"), current.get("recurrence"),
             now, event_id, user_id),
        )
    return get_event(event_id, user_id)


def delete_event(event_id: str, user_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM calendar_events WHERE id = ? AND user_id = ?", (event_id, user_id),
        )
    return cursor.rowcount > 0
