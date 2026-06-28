import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from auth.passwords import hash_password, verify_password
from auth.jwt_utils import create_token, decode_token
from auth.google_oauth import verify_google_token
from api.dependencies import get_current_user
from configs.config import settings
from storage.repositories import user_repo

router = APIRouter(prefix="/auth")
logger = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=1)


class LoginRequest(BaseModel):
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    id_token: str


class AuthResponse(BaseModel):
    token: str
    user: dict


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest):
    existing = user_repo.get_user_by_email(body.email)
    if existing:
        raise HTTPException(409, "Email already registered")

    hashed = hash_password(body.password)
    user = user_repo.create_user(
        email=body.email,
        name=body.name,
        password=hashed,
        auth_provider="local",
    )

    token = create_token(user["id"], user["email"], settings.JWT_SECRET)
    return {"token": token, "user": user}


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest):
    from storage.database import get_connection
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (body.email,)).fetchone()

    if not row:
        raise HTTPException(401, "Invalid email or password")

    user_dict = dict(row)
    if not user_dict.get("password"):
        raise HTTPException(401, "This account uses Google sign-in")

    if not verify_password(body.password, user_dict["password"]):
        raise HTTPException(401, "Invalid email or password")

    user_dict.pop("password", None)
    token = create_token(user_dict["id"], user_dict["email"], settings.JWT_SECRET)
    return {"token": token, "user": user_dict}


@router.post("/google", response_model=AuthResponse)
async def google_auth(body: GoogleAuthRequest):
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(501, "Google OAuth not configured")

    google_user = await verify_google_token(body.id_token, settings.GOOGLE_OAUTH_CLIENT_ID)
    if not google_user:
        raise HTTPException(401, "Invalid Google token")

    existing = user_repo.get_user_by_email(google_user["email"])
    if existing:
        user = existing
    else:
        user = user_repo.create_user(
            email=google_user["email"],
            name=google_user["name"],
            auth_provider="google",
            avatar_url=google_user.get("picture"),
        )

    token = create_token(user["id"], user["email"], settings.JWT_SECRET)
    return {"token": token, "user": user}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


@router.patch("/profile")
def update_profile(body: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    if not body.name:
        raise HTTPException(400, "Nothing to update")
    from storage.database import get_connection
    with get_connection() as conn:
        conn.execute("UPDATE users SET name = ? WHERE id = ?", (body.name, user["id"]))
    updated = user_repo.get_user(user["id"])
    return updated


@router.post("/change-password")
def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    from storage.database import get_connection
    with get_connection() as conn:
        row = conn.execute("SELECT password, auth_provider FROM users WHERE id = ?", (user["id"],)).fetchone()

    if not row:
        raise HTTPException(404, "User not found")

    user_data = dict(row)
    if user_data.get("auth_provider") == "google" and not user_data.get("password"):
        hashed = hash_password(body.new_password)
        with get_connection() as conn:
            conn.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user["id"]))
        return {"status": "password_set"}

    if not user_data.get("password"):
        raise HTTPException(400, "No password set for this account")

    if not verify_password(body.current_password, user_data["password"]):
        raise HTTPException(401, "Current password is incorrect")

    hashed = hash_password(body.new_password)
    with get_connection() as conn:
        conn.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user["id"]))
    return {"status": "password_changed"}
