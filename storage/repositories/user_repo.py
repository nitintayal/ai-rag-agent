"""User repository — dispatches to the active backend."""

from storage.factory import get_backend


def ensure_user(user_id, name=None):
    return get_backend().user.ensure_user(user_id, name)

def get_user(user_id):
    return get_backend().user.get_user(user_id)

def get_user_by_email(email):
    return get_backend().user.get_user_by_email(email)

def create_user(email, name, password=None, auth_provider="local", avatar_url=None):
    return get_backend().user.create_user(email, name, password, auth_provider, avatar_url)
