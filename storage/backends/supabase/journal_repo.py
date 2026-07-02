import json
from datetime import date, datetime, timezone
from typing import Optional
from uuid import uuid4

import numpy as np

from storage.backends.supabase.client import get_supabase


def list_entries(user_id: str, limit: int = 20, offset: int = 0) -> dict:
    sb = get_supabase()
    count_result = sb.table("journal_entries").select("id", count="exact").eq("user_id", user_id).execute()
    total = count_result.count or 0
    result = (sb.table("journal_entries")
              .select("id,user_id,title,content,mood,tags,entry_date,created_at,updated_at")
              .eq("user_id", user_id)
              .order("created_at", desc=True)
              .range(offset, offset + limit - 1)
              .execute())
    items = [_serialize(r) for r in result.data]
    return {"items": items, "total": total, "limit": limit, "offset": offset,
            "has_more": offset + len(items) < total}


def get_entry(entry_id: str, user_id: str) -> Optional[dict]:
    sb = get_supabase()
    result = (sb.table("journal_entries").select("id,user_id,title,content,mood,tags,entry_date,created_at,updated_at")
              .eq("id", entry_id).eq("user_id", user_id).execute())
    return _serialize(result.data[0]) if result.data else None


def add_entry(user_id: str, content: str, title: str | None = None,
              mood: str | None = None, tags: list[str] | None = None,
              entry_date: date | str | None = None) -> dict:
    from storage.backends.embedding_utils import safe_embed, build_search_text
    sb = get_supabase()
    entry_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    ed = str(entry_date or date.today())
    tag_list = tags or []
    search_text = build_search_text(title, content, mood, tag_list)
    embedding = safe_embed(search_text)
    row = {
        "id": entry_id, "user_id": user_id, "title": title, "content": content,
        "mood": mood, "tags": json.dumps(tag_list), "entry_date": ed,
        "embedding": embedding, "created_at": now,
    }
    result = sb.table("journal_entries").insert(row).execute()
    if not result.data:
        raise RuntimeError("Journal entry insert returned no data — Supabase may have rejected it silently")
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
    sb = get_supabase()
    sb.table("journal_entries").update({
        "title": current["title"], "content": current["content"], "mood": current["mood"],
        "tags": json.dumps(current["tags"]), "entry_date": str(current["entry_date"]),
        "embedding": embedding, "updated_at": now,
    }).eq("id", entry_id).eq("user_id", user_id).execute()
    return get_entry(entry_id, user_id)


def delete_entry(entry_id: str, user_id: str) -> bool:
    sb = get_supabase()
    result = sb.table("journal_entries").delete().eq("id", entry_id).eq("user_id", user_id).execute()
    return len(result.data) > 0


def search_entries(user_id: str, query: str, k: int = 5) -> list[dict]:
    sb = get_supabase()
    result = sb.table("journal_entries").select("*").eq("user_id", user_id).execute()
    if not result.data:
        return []

    try:
        from rag.embeddings import embed_query
        query_vec = np.array(embed_query(query), dtype="float32")
        results = []
        for row in result.data:
            serialized = _serialize(row)
            emb_str = row.get("embedding", "[]")
            emb = np.array(json.loads(emb_str), dtype="float32")
            if emb.size == 0:
                continue
            score = float(np.dot(query_vec, emb))
            results.append({"entry": serialized, "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:k]
    except ImportError:
        # No ML libs — fall back to text matching
        q = query.lower()
        results = []
        for row in result.data:
            text = f"{row.get('title', '')} {row.get('content', '')}".lower()
            if q in text:
                results.append({"entry": _serialize(row), "score": 1.0})
        return results[:k]


def _serialize(row: dict) -> dict:
    d = dict(row)
    if isinstance(d.get("tags"), str):
        d["tags"] = json.loads(d["tags"]) if d["tags"] else []
    d["entry_date"] = str(d.get("entry_date", ""))
    d.pop("embedding", None)
    return d
