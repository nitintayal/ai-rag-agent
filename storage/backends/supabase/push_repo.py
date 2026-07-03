"""Supabase push subscription repository."""

from uuid import uuid4
from storage.backends.supabase.client import get_supabase


def save_subscription(user_id: str, endpoint: str, p256dh: str, auth: str) -> dict:
    sb = get_supabase()
    id_ = str(uuid4())
    row = {"id": id_, "user_id": user_id, "endpoint": endpoint, "p256dh": p256dh, "auth": auth}
    sb.table("push_subscriptions").upsert(row, on_conflict="endpoint").execute()
    result = sb.table("push_subscriptions").select("*").eq("endpoint", endpoint).single().execute()
    return result.data


def delete_subscription(user_id: str, endpoint: str) -> bool:
    sb = get_supabase()
    sb.table("push_subscriptions").delete().eq("user_id", user_id).eq("endpoint", endpoint).execute()
    return True


def get_subscriptions_for_user(user_id: str) -> list[dict]:
    sb = get_supabase()
    result = sb.table("push_subscriptions").select("*").eq("user_id", user_id).execute()
    return result.data or []


def get_all_subscriptions() -> list[dict]:
    sb = get_supabase()
    result = sb.table("push_subscriptions").select("*").execute()
    return result.data or []
