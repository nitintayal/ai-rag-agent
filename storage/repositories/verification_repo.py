"""Verification code repository — dispatches to the active backend."""

from storage.factory import get_backend


def create_code(email, code, purpose, expires_at):
    return get_backend().verification.create_code(email, code, purpose, expires_at)

def verify_and_consume(email, code, purpose):
    return get_backend().verification.verify_and_consume(email, code, purpose)

def invalidate_pending(email, purpose):
    return get_backend().verification.invalidate_pending(email, purpose)
