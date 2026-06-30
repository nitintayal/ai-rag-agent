"""Calendar repository — dispatches to the active backend."""

from storage.factory import get_backend


def create_event(user_id, title, start_time, end_time=None, description=None):
    return get_backend().calendar.create_event(user_id, title, start_time, end_time, description)

def list_events(user_id, limit=20):
    return get_backend().calendar.list_events(user_id, limit)

def delete_event(event_id, user_id):
    return get_backend().calendar.delete_event(event_id, user_id)
