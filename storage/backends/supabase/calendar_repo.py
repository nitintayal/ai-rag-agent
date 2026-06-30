from datetime import datetime, timezone
from uuid import uuid4

from storage.backends.supabase.client import get_supabase


def create_event(user_id: str, title: str, start_time: str,
                 end_time: str | None = None, description: str | None = None) -> dict:
    sb = get_supabase()
    eid = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": eid, "user_id": user_id, "title": title, "description": description,
        "start_time": start_time, "end_time": end_time, "created_at": now,
    }
    sb.table("calendar_events").insert(row).execute()
    return row


def list_events(user_id: str, limit: int = 20) -> list[dict]:
    sb = get_supabase()
    result = (sb.table("calendar_events").select("*")
              .eq("user_id", user_id).order("start_time").limit(limit).execute())
    return result.data


def delete_event(event_id: str, user_id: str) -> bool:
    sb = get_supabase()
    result = sb.table("calendar_events").delete().eq("id", event_id).eq("user_id", user_id).execute()
    return len(result.data) > 0
