"""SQLite push subscription repository."""

from uuid import uuid4
from storage.database import get_connection


def save_subscription(user_id: str, endpoint: str, p256dh: str, auth: str) -> dict:
    with get_connection() as conn:
        id_ = str(uuid4())
        conn.execute(
            """INSERT INTO push_subscriptions (id, user_id, endpoint, p256dh, auth)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(endpoint) DO UPDATE SET user_id=excluded.user_id,
               p256dh=excluded.p256dh, auth=excluded.auth""",
            (id_, user_id, endpoint, p256dh, auth),
        )
        row = conn.execute("SELECT * FROM push_subscriptions WHERE endpoint=?", (endpoint,)).fetchone()
        return dict(row)


def delete_subscription(user_id: str, endpoint: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM push_subscriptions WHERE user_id=? AND endpoint=?",
            (user_id, endpoint),
        )
        return cur.rowcount > 0


def get_subscriptions_for_user(user_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM push_subscriptions WHERE user_id=?", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_subscriptions() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM push_subscriptions").fetchall()
        return [dict(r) for r in rows]
