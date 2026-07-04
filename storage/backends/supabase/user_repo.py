from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from storage.backends.supabase.client import get_supabase


def ensure_user(user_id: str, name: str | None = None) -> dict:
    sb = get_supabase()
    result = sb.table("users").select("*").eq("id", user_id).execute()
    if result.data:
        return _serialize(result.data[0])
    now = datetime.now(timezone.utc).isoformat()
    row = {"id": user_id, "name": name or user_id, "created_at": now}
    sb.table("users").insert(row).execute()
    return row


def get_user(user_id: str) -> Optional[dict]:
    sb = get_supabase()
    result = sb.table("users").select("*").eq("id", user_id).execute()
    return _serialize(result.data[0]) if result.data else None


def get_user_by_email(email: str) -> Optional[dict]:
    sb = get_supabase()
    result = sb.table("users").select("*").eq("email", email).execute()
    return _serialize(result.data[0]) if result.data else None


def get_user_by_email_with_password(email: str) -> Optional[dict]:
    """Internal use only — includes the password hash. Never expose via API."""
    sb = get_supabase()
    result = sb.table("users").select("*").eq("email", email).execute()
    return result.data[0] if result.data else None


def create_user(email: str, name: str, password: str | None = None,
                auth_provider: str = "local", avatar_url: str | None = None) -> dict:
    sb = get_supabase()
    user_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": user_id, "name": name, "email": email, "password": password,
        "avatar_url": avatar_url, "auth_provider": auth_provider,
        "email_verified": False, "created_at": now,
    }
    sb.table("users").insert(row).execute()
    # Fetch from DB so returned shape matches get_user() (has_llm_api_key, db defaults, etc.)
    return get_user(user_id) or _serialize(row)


def get_user_api_key(user_id: str) -> Optional[str]:
    """Returns the raw llm_api_key — internal use only, never expose via API."""
    sb = get_supabase()
    result = sb.table("users").select("llm_api_key").eq("id", user_id).execute()
    return result.data[0].get("llm_api_key") if result.data else None


def update_user(user_id: str, **fields) -> Optional[dict]:
    allowed = {"name", "password", "avatar_url", "email_verified", "llm_provider", "llm_model", "llm_api_key"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_user(user_id)
    sb = get_supabase()
    sb.table("users").update(updates).eq("id", user_id).execute()
    return get_user(user_id)


def _serialize(row: dict) -> dict:
    d = dict(row)
    d.pop("password", None)
    d["has_llm_api_key"] = bool(d.pop("llm_api_key", None))
    return d
