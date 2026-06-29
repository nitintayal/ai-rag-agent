"""Memory repository — dispatches to the active backend."""

from storage.factory import get_backend


def store_memory(user_id, key, value, category="general", embedding=None):
    return get_backend().memory.store_memory(user_id, key, value, category, embedding)

def get_memory(user_id, key):
    return get_backend().memory.get_memory(user_id, key)

def list_memories(user_id, category=None):
    return get_backend().memory.list_memories(user_id, category)

def search_memories(user_id, query_embedding, k=5):
    return get_backend().memory.search_memories(user_id, query_embedding, k)

def delete_memory(user_id, key):
    return get_backend().memory.delete_memory(user_id, key)
