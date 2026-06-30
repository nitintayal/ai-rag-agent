from datetime import datetime, timezone
from uuid import uuid4

from storage.database import get_connection


def create_code(email: str, code: str, purpose: str, expires_at: str) -> dict:
    vid = str(uuid4())
    with get_connection() as conn:
        conn.execute(
            "UPDATE verification_codes SET used = 1 WHERE email = ? AND purpose = ? AND used = 0",
            (email, purpose),
        )
        conn.execute(
            "INSERT INTO verification_codes (id, email, code, purpose, expires_at) VALUES (?, ?, ?, ?, ?)",
            (vid, email, code, purpose, expires_at),
        )
    return {"id": vid, "email": email, "code": code, "purpose": purpose, "expires_at": expires_at}


def verify_and_consume(email: str, code: str, purpose: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM verification_codes WHERE email = ? AND code = ? AND purpose = ? AND used = 0 AND expires_at > ?",
            (email, code, purpose, now),
        ).fetchone()
        if not row:
            return False
        conn.execute("UPDATE verification_codes SET used = 1 WHERE id = ?", (row["id"],))
    return True


def invalidate_pending(email: str, purpose: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE verification_codes SET used = 1 WHERE email = ? AND purpose = ? AND used = 0",
            (email, purpose),
        )
