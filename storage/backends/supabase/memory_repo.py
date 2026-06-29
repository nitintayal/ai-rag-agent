import json
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import numpy as np

from storage.backends.supabase.client import get_supabase


def store_memory(user_id: str, key: str, value: str, category: str = "general",
                 embedding: list[float] | None = None) -> dict:
    sb = get_supabase()
    now = datetime.now(timezone.utc).isoformat()
    emb_json = json.dumps(embedding) if embedding else None

    result = sb.table("user_memories").select("id").eq("user_id", user_id).eq("key", key).execute()
    if result.data:
        mem_id = result.data[0]["id"]
        sb.table("user_memories").update({
            "value": value, "category": category, "embedding": emb_json, "updated_at": now,
        }).eq("id", mem_id).execute()
    else:
        mem_id = str(uuid4())
        sb.table("user_memories").insert({
            "id": mem_id, "user_id": user_id, "key": key, "value": value,
            "category": category, "embedding": emb_json, "created_at": now,
        }).execute()

    return {"id": mem_id, "user_id": user_id, "key": key, "value": value,
            "category": category, "created_at": now}


def get_memory(user_id: str, key: str) -> Optional[dict]:
    sb = get_supabase()
    result = sb.table("user_memories").select("*").eq("user_id", user_id).eq("key", key).execute()
    return result.data[0] if result.data else None


def list_memories(user_id: str, category: str | None = None) -> list[dict]:
    sb = get_supabase()
    query = sb.table("user_memories").select("id,user_id,key,value,category,created_at,updated_at").eq("user_id", user_id)
    if category:
        query = query.eq("category", category)
    return query.execute().data


def search_memories(user_id: str, query_embedding: list[float], k: int = 5) -> list[dict]:
    sb = get_supabase()
    result = sb.table("user_memories").select("*").eq("user_id", user_id).not_.is_("embedding", "null").execute()
    if not result.data:
        return []
    query_vec = np.array(query_embedding, dtype="float32")
    results = []
    for row in result.data:
        emb = np.array(json.loads(row["embedding"]), dtype="float32")
        score = float(np.dot(query_vec, emb))
        d = dict(row)
        d.pop("embedding", None)
        results.append({"memory": d, "score": score})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]


def delete_memory(user_id: str, key: str) -> bool:
    sb = get_supabase()
    result = sb.table("user_memories").delete().eq("user_id", user_id).eq("key", key).execute()
    return len(result.data) > 0
