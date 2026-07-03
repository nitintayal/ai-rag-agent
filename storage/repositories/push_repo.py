"""Push subscription repository — dispatches to the active backend."""

from storage.factory import get_backend


def save_subscription(user_id: str, endpoint: str, p256dh: str, auth: str) -> dict:
    return get_backend().push.save_subscription(user_id, endpoint, p256dh, auth)


def delete_subscription(user_id: str, endpoint: str) -> bool:
    return get_backend().push.delete_subscription(user_id, endpoint)


def get_subscriptions_for_user(user_id: str) -> list[dict]:
    return get_backend().push.get_subscriptions_for_user(user_id)


def get_all_subscriptions() -> list[dict]:
    return get_backend().push.get_all_subscriptions()
