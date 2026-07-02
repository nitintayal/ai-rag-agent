"""User repository — dispatches to the active backend."""

from storage.factory import get_backend


def ensure_user(user_id, name=None):
    return get_backend().user.ensure_user(user_id, name)

def get_user(user_id):
    return get_backend().user.get_user(user_id)

def get_user_by_email(email):
    return get_backend().user.get_user_by_email(email)

def get_user_by_email_with_password(email):
    return get_backend().user.get_user_by_email_with_password(email)

def create_user(email, name, password=None, auth_provider="local", avatar_url=None):
    return get_backend().user.create_user(email, name, password, auth_provider, avatar_url)

def update_user(user_id, **fields):
    return get_backend().user.update_user(user_id, **fields)

def get_user_api_key(user_id):
    return get_backend().user.get_user_api_key(user_id)
