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
    from embeddings.sentence_embeddings import embed_query
    sb = get_supabase()
    entry_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    ed = str(entry_date or date.today())
    tag_list = tags or []
    search_text = _build_search_text(title, content, mood, tag_list)
    embedding = json.dumps(embed_query(search_text).tolist())
    row = {
        "id": entry_id, "user_id": user_id, "title": title, "content": content,
        "mood": mood, "tags": json.dumps(tag_list), "entry_date": ed,
        "embedding": embedding, "created_at": now,
    }
    sb.table("journal_entries").insert(row).execute()
    return {"id": entry_id, "user_id": user_id, "title": title, "content": content,
            "mood": mood, "tags": tag_list, "entry_date": ed, "created_at": now, "updated_at": None}


def update_entry(entry_id: str, user_id: str, **fields) -> Optional[dict]:
    from embeddings.sentence_embeddings import embed_query
    current = get_entry(entry_id, user_id)
    if not current:
        return None
    for key, val in fields.items():
        if val is not None:
            current[key] = val
    now = datetime.now(timezone.utc).isoformat()
    search_text = _build_search_text(current["title"], current["content"], current["mood"], current["tags"])
    embedding = json.dumps(embed_query(search_text).tolist())
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
    from embeddings.sentence_embeddings import embed_query
    sb = get_supabase()
    result = sb.table("journal_entries").select("*").eq("user_id", user_id).execute()
    if not result.data:
        return []
    query_vec = np.array(embed_query(query), dtype="float32")
    results = []
    for row in result.data:
        serialized = _serialize(row)
        emb = np.array(json.loads(row["embedding"]), dtype="float32")
        score = float(np.dot(query_vec, emb))
        results.append({"entry": serialized, "score": score})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]


def _serialize(row: dict) -> dict:
    d = dict(row)
    if isinstance(d.get("tags"), str):
        d["tags"] = json.loads(d["tags"]) if d["tags"] else []
    d["entry_date"] = str(d.get("entry_date", ""))
    d.pop("embedding", None)
    return d


def _build_search_text(title, content, mood, tags) -> str:
    tag_str = " ".join(tags) if tags else ""
    return "\n".join(p for p in [title or "", content or "", mood or "", tag_str] if p)
