import json
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import numpy as np

from storage.database import get_connection


def store_memory(user_id: str, key: str, value: str, category: str = "general",
                 embedding: list[float] | None = None) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    emb_json = json.dumps(embedding) if embedding else None

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM user_memories WHERE user_id = ? AND key = ?",
            (user_id, key),
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE user_memories SET value=?, category=?, embedding=?, updated_at=?
                   WHERE user_id=? AND key=?""",
                (value, category, emb_json, now, user_id, key),
            )
            mem_id = existing["id"]
        else:
            mem_id = str(uuid4())
            conn.execute(
                """INSERT INTO user_memories (id, user_id, key, value, category, embedding, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (mem_id, user_id, key, value, category, emb_json, now),
            )

    return {"id": mem_id, "user_id": user_id, "key": key, "value": value,
            "category": category, "created_at": now}


def get_memory(user_id: str, key: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_memories WHERE user_id = ? AND key = ?",
            (user_id, key),
        ).fetchone()
    return dict(row) if row else None


def list_memories(user_id: str, category: str | None = None) -> list[dict]:
    with get_connection() as conn:
        if category:
            rows = conn.execute(
                "SELECT id, user_id, key, value, category, created_at, updated_at FROM user_memories WHERE user_id = ? AND category = ?",
                (user_id, category),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, user_id, key, value, category, created_at, updated_at FROM user_memories WHERE user_id = ?",
                (user_id,),
            ).fetchall()
    return [dict(r) for r in rows]


def search_memories(user_id: str, query_embedding: list[float], k: int = 5) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM user_memories WHERE user_id = ? AND embedding IS NOT NULL",
            (user_id,),
        ).fetchall()

    if not rows:
        return []

    query_vec = np.array(query_embedding, dtype="float32")
    results = []
    for row in rows:
        emb = np.array(json.loads(row["embedding"]), dtype="float32")
        score = float(np.dot(query_vec, emb))
        d = dict(row)
        del d["embedding"]
        results.append({"memory": d, "score": score})

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]


def delete_memory(user_id: str, key: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM user_memories WHERE user_id = ? AND key = ?",
            (user_id, key),
        )
    return cursor.rowcount > 0
