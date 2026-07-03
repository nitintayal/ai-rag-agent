"""Calendar repository — dispatches to the active backend."""

from storage.factory import get_backend


def create_event(user_id, title, start_time, end_time=None, description=None,
                 location=None, all_day=False, recurrence=None):
    return get_backend().calendar.create_event(
        user_id, title, start_time, end_time, description, location, all_day, recurrence)

def get_event(event_id, user_id):
    return get_backend().calendar.get_event(event_id, user_id)

def list_events(user_id, limit=50, start=None, end=None):
    return get_backend().calendar.list_events(user_id, limit, start, end)

def update_event(event_id, user_id, **fields):
    return get_backend().calendar.update_event(event_id, user_id, **fields)

def delete_event(event_id, user_id):
    return get_backend().calendar.delete_event(event_id, user_id)
