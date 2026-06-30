"""Email verification / password reset code generation and validation."""

import secrets
from datetime import datetime, timedelta, timezone

from storage.repositories import verification_repo


def create_verification_code(email: str, purpose: str) -> str:
    code = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    verification_repo.create_code(email, code, purpose, expires)
    return code


def verify_code(email: str, code: str, purpose: str) -> bool:
    return verification_repo.verify_and_consume(email, code, purpose)
