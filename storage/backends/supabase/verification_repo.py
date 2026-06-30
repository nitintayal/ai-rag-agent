from datetime import datetime, timezone
from uuid import uuid4

from storage.backends.supabase.client import get_supabase


def create_code(email: str, code: str, purpose: str, expires_at: str) -> dict:
    sb = get_supabase()
    vid = str(uuid4())
    sb.table("verification_codes").update({"used": True}).eq("email", email).eq("purpose", purpose).eq("used", False).execute()
    row = {"id": vid, "email": email, "code": code, "purpose": purpose, "expires_at": expires_at, "used": False}
    sb.table("verification_codes").insert(row).execute()
    return row


def verify_and_consume(email: str, code: str, purpose: str) -> bool:
    sb = get_supabase()
    now = datetime.now(timezone.utc).isoformat()
    result = (sb.table("verification_codes").select("id")
              .eq("email", email).eq("code", code).eq("purpose", purpose).eq("used", False)
              .gt("expires_at", now).execute())
    if not result.data:
        return False
    sb.table("verification_codes").update({"used": True}).eq("id", result.data[0]["id"]).execute()
    return True


def invalidate_pending(email: str, purpose: str) -> None:
    sb = get_supabase()
    sb.table("verification_codes").update({"used": True}).eq("email", email).eq("purpose", purpose).eq("used", False).execute()
