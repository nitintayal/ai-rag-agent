import json
from datetime import date, datetime, timezone
from typing import Optional
from uuid import uuid4

import numpy as np

from storage.database import get_connection


def list_entries(user_id: str, limit: int = 20, offset: int = 0) -> dict:
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM journal_entries WHERE user_id = ?", (user_id,),
        ).fetchone()[0]
        rows = conn.execute(
            """SELECT id, user_id, title, content, mood, tags, entry_date, created_at, updated_at
               FROM journal_entries WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (user_id, limit, offset),
        ).fetchall()
    items = [_serialize_row(row) for row in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset,
            "has_more": offset + len(items) < total}


def get_entry(entry_id: str, user_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            """SELECT id, user_id, title, content, mood, tags, entry_date, created_at, updated_at
               FROM journal_entries WHERE id = ? AND user_id = ?""",
            (entry_id, user_id),
        ).fetchone()
    return _serialize_row(row) if row else None


def add_entry(user_id: str, content: str, title: str | None = None,
              mood: str | None = None, tags: list[str] | None = None,
              entry_date: date | None = None) -> dict:
    from storage.backends.embedding_utils import safe_embed, build_search_text

    now = datetime.now(timezone.utc).isoformat()
    ed = str(entry_date or date.today())
    entry_id = str(uuid4())
    tag_list = tags or []

    search_text = build_search_text(title, content, mood, tag_list)
    embedding = safe_embed(search_text)

    with get_connection() as conn:
        conn.execute(
            """INSERT INTO journal_entries
               (id, user_id, title, content, mood, tags, entry_date, embedding, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entry_id, user_id, title, content, mood, json.dumps(tag_list), ed, embedding, now),
        )
    return {"id": entry_id, "user_id": user_id, "title": title, "content": content,
            "mood": mood, "tags": tag_list, "entry_date": ed, "created_at": now, "updated_at": None}


def update_entry(entry_id: str, user_id: str, **fields) -> Optional[dict]:
    from storage.backends.embedding_utils import safe_embed, build_search_text

    current = get_entry(entry_id, user_id)
    if not current:
        return None

    for key, val in fields.items():
        if val is not None:
            current[key] = val

    now = datetime.now(timezone.utc).isoformat()
    search_text = build_search_text(current["title"], current["content"], current["mood"], current["tags"])
    embedding = safe_embed(search_text)

    with get_connection() as conn:
        conn.execute(
            """UPDATE journal_entries
               SET title=?, content=?, mood=?, tags=?, entry_date=?, embedding=?, updated_at=?
               WHERE id=? AND user_id=?""",
            (current["title"], current["content"], current["mood"],
             json.dumps(current["tags"]), str(current["entry_date"]),
             embedding, now, entry_id, user_id),
        )
    return get_entry(entry_id, user_id)


def delete_entry(entry_id: str, user_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM journal_entries WHERE id = ? AND user_id = ?",
            (entry_id, user_id),
        )
    return cursor.rowcount > 0


def search_entries(user_id: str, query: str, k: int = 5) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, user_id, title, content, mood, tags, entry_date, embedding, created_at, updated_at
               FROM journal_entries WHERE user_id = ?""",
            (user_id,),
        ).fetchall()

    if not rows:
        return []

    try:
        from rag.embeddings import embed_query
        query_vec = np.array(embed_query(query), dtype="float32")
        results = []
        for row in rows:
            serialized = _serialize_row(row)
            emb = np.array(json.loads(row["embedding"]), dtype="float32")
            if emb.size == 0:
                continue
            score = float(np.dot(query_vec, emb))
            results.append({"entry": serialized, "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:k]
    except ImportError:
        q = query.lower().strip()
        results = []
        for row in rows:
            text = f"{row['title'] or ''} {row['content'] or ''}".lower()
            words = [w for w in q.split() if len(w) > 3 and w not in {"show", "search", "find", "my", "the", "and", "journal", "entries"}]
            if not words or any(w in text for w in words):
                results.append({"entry": _serialize_row(row), "score": 1.0})
        return results[:k]


def _serialize_row(row) -> dict:
    d = dict(row)
    d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
    d["entry_date"] = str(d["entry_date"])
    return d
