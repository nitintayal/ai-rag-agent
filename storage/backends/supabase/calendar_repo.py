from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from storage.backends.supabase.client import get_supabase


def create_event(user_id: str, title: str, start_time: str,
                 end_time: str | None = None, description: str | None = None,
                 location: str | None = None, all_day: bool = False,
                 recurrence: str | None = None) -> dict:
    sb = get_supabase()
    eid = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": eid, "user_id": user_id, "title": title, "description": description,
        "start_time": start_time, "end_time": end_time, "all_day": all_day,
        "location": location, "recurrence": recurrence, "created_at": now,
    }
    sb.table("calendar_events").insert(row).execute()
    return {**row, "updated_at": None}


def get_event(event_id: str, user_id: str) -> Optional[dict]:
    sb = get_supabase()
    result = sb.table("calendar_events").select("*").eq("id", event_id).eq("user_id", user_id).execute()
    return result.data[0] if result.data else None


def list_events(user_id: str, limit: int = 50,
                start: str | None = None, end: str | None = None) -> list[dict]:
    sb = get_supabase()
    query = sb.table("calendar_events").select("*").eq("user_id", user_id)
    if start:
        query = query.gte("start_time", start)
    if end:
        query = query.lte("start_time", end)
    result = query.order("start_time").limit(limit).execute()
    return result.data


def update_event(event_id: str, user_id: str, **fields) -> Optional[dict]:
    current = get_event(event_id, user_id)
    if not current:
        return None
    allowed = {"title", "description", "start_time", "end_time", "all_day", "location", "recurrence"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    sb = get_supabase()
    sb.table("calendar_events").update(updates).eq("id", event_id).eq("user_id", user_id).execute()
    return get_event(event_id, user_id)


def delete_event(event_id: str, user_id: str) -> bool:
    sb = get_supabase()
    result = sb.table("calendar_events").delete().eq("id", event_id).eq("user_id", user_id).execute()
    return len(result.data) > 0
