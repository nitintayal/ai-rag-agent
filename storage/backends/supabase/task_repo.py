from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from storage.backends.supabase.client import get_supabase


def create_task(user_id: str, title: str, description: str | None = None,
                due_date: str | None = None, priority: str = "medium",
                recurrence: str | None = None) -> dict:
    sb = get_supabase()
    task_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": task_id, "user_id": user_id, "title": title,
        "description": description, "due_date": due_date,
        "status": "pending", "priority": priority, "recurrence": recurrence, "created_at": now,
    }
    sb.table("tasks").insert(row).execute()
    return {**row, "reminder_sent_at": None, "updated_at": None}


def list_tasks(user_id: str, status: str | None = None, limit: int = 50) -> list[dict]:
    sb = get_supabase()
    query = sb.table("tasks").select("*").eq("user_id", user_id)
    if status:
        query = query.eq("status", status)
    result = query.order("due_date", desc=False, nullsfirst=False).order("created_at", desc=True).limit(limit).execute()
    return result.data


def get_task(task_id: str, user_id: str) -> Optional[dict]:
    sb = get_supabase()
    result = sb.table("tasks").select("*").eq("id", task_id).eq("user_id", user_id).execute()
    return result.data[0] if result.data else None


def update_task(task_id: str, user_id: str, **fields) -> Optional[dict]:
    current = get_task(task_id, user_id)
    if not current:
        return None

    completing = fields.get("status") == "done" and current.get("status") != "done"

    allowed = {"title", "description", "due_date", "status", "priority", "recurrence", "reminder_sent_at"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    sb = get_supabase()
    sb.table("tasks").update(updates).eq("id", task_id).eq("user_id", user_id).execute()

    if completing and current.get("recurrence") and current.get("due_date"):
        _spawn_next_recurrence(user_id, {**current, **fields})

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
            day = min(due.day, [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            next_due = due.replace(year=year, month=month, day=day)
        else:
            return
        create_task(user_id, task["title"], task.get("description"),
                    str(next_due), task["priority"], task["recurrence"])
    except Exception:
        pass


def delete_task(task_id: str, user_id: str) -> bool:
    sb = get_supabase()
    result = sb.table("tasks").delete().eq("id", task_id).eq("user_id", user_id).execute()
    return len(result.data) > 0


def get_tasks_due_today(user_id: str | None = None) -> list[dict]:
    today = date.today().isoformat()
    sb = get_supabase()
    query = (sb.table("tasks")
             .select("*, users(email, name)")
             .lte("due_date", today)
             .not_.in_("status", ["done", "cancelled"])
             .or_(f"reminder_sent_at.is.null,reminder_sent_at.lt.{today}"))
    if user_id:
        query = query.eq("user_id", user_id)
    result = query.execute()
    return result.data


def mark_reminder_sent(task_id: str) -> None:
    today = date.today().isoformat()
    sb = get_supabase()
    sb.table("tasks").update({"reminder_sent_at": today}).eq("id", task_id).execute()
