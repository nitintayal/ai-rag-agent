"""FastAPI dependencies for auth and database."""

from typing import Optional

from fastapi import Header, HTTPException

from auth.jwt_utils import decode_token
from configs.config import settings
from storage.repositories import user_repo


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization:
        raise HTTPException(401, "Not authenticated")

    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    payload = decode_token(token, settings.JWT_SECRET)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")

    user = user_repo.get_user(payload["sub"])
    if not user:
        user = user_repo.ensure_user(payload["sub"], payload.get("email", ""))
    return user
