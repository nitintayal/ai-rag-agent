import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from auth.passwords import hash_password, verify_password
from auth.jwt_utils import create_token, decode_token
from auth.google_oauth import verify_google_token
from auth.email import send_verification_email, send_password_reset_email
from api.dependencies import get_current_user
from configs.config import settings
from storage.database import get_connection
from storage.repositories import user_repo

router = APIRouter(prefix="/auth")
logger = logging.getLogger(__name__)

_login_attempts: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 5
_RATE_WINDOW = 60


def _check_rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < _RATE_WINDOW]
    if len(_login_attempts[ip]) >= _RATE_LIMIT:
        raise HTTPException(429, "Too many attempts. Try again in a minute.")
    _login_attempts[ip].append(now)


def _create_verification_code(email: str, purpose: str) -> str:
    code = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    vid = secrets.token_hex(16)
    with get_connection() as conn:
        conn.execute(
            "UPDATE verification_codes SET used = 1 WHERE email = ? AND purpose = ? AND used = 0",
            (email, purpose),
        )
        conn.execute(
            "INSERT INTO verification_codes (id, email, code, purpose, expires_at) VALUES (?, ?, ?, ?, ?)",
            (vid, email, code, purpose, expires),
        )
    return code


def _verify_code(email: str, code: str, purpose: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM verification_codes WHERE email = ? AND code = ? AND purpose = ? AND used = 0 AND expires_at > ?",
            (email, code, purpose, now),
        ).fetchone()
        if not row:
            return False
        conn.execute("UPDATE verification_codes SET used = 1 WHERE id = ?", (row["id"],))
    return True


# ── Schemas ──────────────────────────────────────────────────────

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

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str = Field(..., min_length=6)

class VerifyEmailRequest(BaseModel):
    email: str
    code: str

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


# ── Register ─────────────────────────────────────────────────────

class RegisterResponse(BaseModel):
    status: str
    message: str


@router.post("/register", response_model=RegisterResponse)
def register(body: RegisterRequest, request: Request):
    _check_rate_limit(request)

    existing = user_repo.get_user_by_email(body.email)
    if existing:
        raise HTTPException(409, "Email already registered")

    hashed = hash_password(body.password)
    user_repo.create_user(
        email=body.email,
        name=body.name,
        password=hashed,
        auth_provider="local",
    )

    code = _create_verification_code(body.email, "email_verify")
    send_verification_email(body.email, code, settings.FRONTEND_URL)

    return {"status": "verification_sent", "message": "Check your email for a verification link."}


# ── Verify Email ─────────────────────────────────────────────────

@router.post("/verify-email")
def verify_email(body: VerifyEmailRequest):
    if not _verify_code(body.email, body.code, "email_verify"):
        raise HTTPException(400, "Invalid or expired verification code")

    with get_connection() as conn:
        conn.execute("UPDATE users SET email_verified = 1 WHERE email = ?", (body.email,))

    user = user_repo.get_user_by_email(body.email)
    if not user:
        raise HTTPException(404, "User not found")

    token = create_token(user["id"], user["email"], settings.JWT_SECRET)
    return {"status": "email_verified", "token": token, "user": user}


# ── Login ────────────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, request: Request):
    _check_rate_limit(request)

    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (body.email,)).fetchone()

    if not row:
        raise HTTPException(401, "Invalid email or password")

    user_dict = dict(row)
    if not user_dict.get("password"):
        raise HTTPException(401, "This account uses Google sign-in")

    if not verify_password(body.password, user_dict["password"]):
        raise HTTPException(401, "Invalid email or password")

    if not user_dict.get("email_verified"):
        code = _create_verification_code(body.email, "email_verify")
        send_verification_email(body.email, code, settings.FRONTEND_URL)
        raise HTTPException(403, "Email not verified. A new verification link has been sent.")

    user_dict.pop("password", None)
    token = create_token(user_dict["id"], user_dict["email"], settings.JWT_SECRET)
    return {"token": token, "user": user_dict}


# ── Google OAuth ─────────────────────────────────────────────────

@router.post("/google", response_model=AuthResponse)
async def google_auth(body: GoogleAuthRequest):
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(501, "Google OAuth not configured")

    google_user = await verify_google_token(body.id_token, settings.GOOGLE_OAUTH_CLIENT_ID)
    if not google_user:
        raise HTTPException(401, "Invalid Google token")

    existing = user_repo.get_user_by_email(google_user["email"])
    if existing:
        if not existing.get("email_verified"):
            with get_connection() as conn:
                conn.execute("UPDATE users SET email_verified = 1 WHERE email = ?", (google_user["email"],))
        user = user_repo.get_user_by_email(google_user["email"])
    else:
        user = user_repo.create_user(
            email=google_user["email"],
            name=google_user["name"],
            auth_provider="google",
            avatar_url=google_user.get("picture"),
        )
        with get_connection() as conn:
            conn.execute("UPDATE users SET email_verified = 1 WHERE email = ?", (google_user["email"],))
        user = user_repo.get_user_by_email(google_user["email"])

    token = create_token(user["id"], user["email"], settings.JWT_SECRET)
    return {"token": token, "user": user}


# ── Forgot / Reset Password ─────────────────────────────────────

@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, request: Request):
    _check_rate_limit(request)

    user = user_repo.get_user_by_email(body.email)
    if user:
        code = _create_verification_code(body.email, "password_reset")
        send_password_reset_email(body.email, code, settings.FRONTEND_URL)

    return {"message": "If this email exists, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, request: Request):
    _check_rate_limit(request)

    if not _verify_code(body.email, body.code, "password_reset"):
        raise HTTPException(400, "Invalid or expired reset code")

    user = user_repo.get_user_by_email(body.email)
    if not user:
        raise HTTPException(404, "User not found")

    hashed = hash_password(body.new_password)
    with get_connection() as conn:
        conn.execute("UPDATE users SET password = ? WHERE email = ?", (hashed, body.email))

    return {"status": "password_reset"}


# ── Profile ──────────────────────────────────────────────────────

@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.patch("/profile")
def update_profile(body: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    if not body.name:
        raise HTTPException(400, "Nothing to update")
    with get_connection() as conn:
        conn.execute("UPDATE users SET name = ? WHERE id = ?", (body.name, user["id"]))
    return user_repo.get_user(user["id"])


@router.post("/change-password")
def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user)):
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
        raise HTTPException(400, "No password set")

    if not verify_password(body.current_password, user_data["password"]):
        raise HTTPException(401, "Current password is incorrect")

    hashed = hash_password(body.new_password)
    with get_connection() as conn:
        conn.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user["id"]))
    return {"status": "password_changed"}
