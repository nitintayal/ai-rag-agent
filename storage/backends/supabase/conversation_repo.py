from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from storage.backends.supabase.client import get_supabase


def create_conversation(user_id: str, title: str | None = None, conversation_id: str | None = None) -> dict:
    sb = get_supabase()
    cid = conversation_id or str(uuid4())
    result = sb.table("conversations").select("*").eq("id", cid).execute()
    if result.data:
        return result.data[0]
    now = datetime.now(timezone.utc).isoformat()
    row = {"id": cid, "user_id": user_id, "title": title, "created_at": now}
    sb.table("conversations").insert(row).execute()
    return row


def get_conversation(conversation_id: str) -> Optional[dict]:
    sb = get_supabase()
    result = sb.table("conversations").select("*").eq("id", conversation_id).execute()
    return result.data[0] if result.data else None


def list_conversations(user_id: str, limit: int = 20, offset: int = 0) -> list[dict]:
    sb = get_supabase()
    result = (sb.table("conversations").select("*")
              .eq("user_id", user_id)
              .order("created_at", desc=True)
              .range(offset, offset + limit - 1)
              .execute())
    return result.data


def add_message(conversation_id: str, role: str, content: str,
                tool_name: str | None = None, tool_result: str | None = None) -> dict:
    sb = get_supabase()
    msg_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": msg_id, "conversation_id": conversation_id, "role": role,
        "content": content, "tool_name": tool_name, "tool_result": tool_result,
        "created_at": now,
    }
    sb.table("messages").insert(row).execute()
    sb.table("conversations").update({"updated_at": now}).eq("id", conversation_id).execute()
    return row


def get_messages(conversation_id: str, limit: int = 20) -> list[dict]:
    sb = get_supabase()
    result = (sb.table("messages").select("*")
              .eq("conversation_id", conversation_id)
              .order("created_at", desc=True)
              .limit(limit)
              .execute())
    return list(reversed(result.data))


def delete_conversation(conversation_id: str) -> bool:
    sb = get_supabase()
    sb.table("messages").delete().eq("conversation_id", conversation_id).execute()
    result = sb.table("conversations").delete().eq("id", conversation_id).execute()
    return len(result.data) > 0
