"""Task repository — dispatches to the active backend."""

from storage.factory import get_backend


def create_task(user_id, title, description=None, due_date=None, priority="medium"):
    return get_backend().task.create_task(user_id, title, description, due_date, priority)

def list_tasks(user_id, status=None, limit=50):
    return get_backend().task.list_tasks(user_id, status, limit)

def get_task(task_id, user_id):
    return get_backend().task.get_task(task_id, user_id)

def update_task(task_id, user_id, **fields):
    return get_backend().task.update_task(task_id, user_id, **fields)

def delete_task(task_id, user_id):
    return get_backend().task.delete_task(task_id, user_id)
