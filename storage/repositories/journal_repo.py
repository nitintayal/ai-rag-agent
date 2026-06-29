"""Journal repository — dispatches to the active backend."""

from storage.factory import get_backend


def list_entries(user_id, limit=20, offset=0):
    return get_backend().journal.list_entries(user_id, limit, offset)

def get_entry(entry_id, user_id):
    return get_backend().journal.get_entry(entry_id, user_id)

def add_entry(user_id, content, title=None, mood=None, tags=None, entry_date=None):
    return get_backend().journal.add_entry(user_id, content, title, mood, tags, entry_date)

def update_entry(entry_id, user_id, **fields):
    return get_backend().journal.update_entry(entry_id, user_id, **fields)

def delete_entry(entry_id, user_id):
    return get_backend().journal.delete_entry(entry_id, user_id)

def search_entries(user_id, query, k=5):
    return get_backend().journal.search_entries(user_id, query, k)
