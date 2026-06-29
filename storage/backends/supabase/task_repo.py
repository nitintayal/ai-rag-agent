from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from storage.backends.supabase.client import get_supabase


def create_task(user_id: str, title: str, description: str | None = None,
                due_date: str | None = None, priority: str = "medium") -> dict:
    sb = get_supabase()
    task_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": task_id, "user_id": user_id, "title": title,
        "description": description, "due_date": due_date,
        "status": "pending", "priority": priority, "created_at": now,
    }
    sb.table("tasks").insert(row).execute()
    return row


def list_tasks(user_id: str, status: str | None = None, limit: int = 50) -> list[dict]:
    sb = get_supabase()
    query = sb.table("tasks").select("*").eq("user_id", user_id)
    if status:
        query = query.eq("status", status)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return result.data


def get_task(task_id: str, user_id: str) -> Optional[dict]:
    sb = get_supabase()
    result = sb.table("tasks").select("*").eq("id", task_id).eq("user_id", user_id).execute()
    return result.data[0] if result.data else None


def update_task(task_id: str, user_id: str, **fields) -> Optional[dict]:
    current = get_task(task_id, user_id)
    if not current:
        return None
    for key, val in fields.items():
        if val is not None:
            current[key] = val
    now = datetime.now(timezone.utc).isoformat()
    sb = get_supabase()
    sb.table("tasks").update({
        "title": current["title"], "description": current["description"],
        "due_date": current["due_date"], "status": current["status"],
        "priority": current["priority"], "updated_at": now,
    }).eq("id", task_id).eq("user_id", user_id).execute()
    return get_task(task_id, user_id)


def delete_task(task_id: str, user_id: str) -> bool:
    sb = get_supabase()
    result = sb.table("tasks").delete().eq("id", task_id).eq("user_id", user_id).execute()
    return len(result.data) > 0
