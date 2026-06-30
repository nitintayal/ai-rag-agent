import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from auth.passwords import hash_password, verify_password
from auth.jwt_utils import create_token
from auth.google_oauth import verify_google_token
from auth.email import send_verification_email, send_password_reset_email
from api.dependencies import get_current_user
from configs.config import settings
from storage.repositories import user_repo, verification_repo

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
    verification_repo.create_code(email, code, purpose, expires)
    return code


def _verify_code(email: str, code: str, purpose: str) -> bool:
    return verification_repo.verify_and_consume(email, code, purpose)


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

@router.post("/register")
def register(body: RegisterRequest, request: Request):
    _check_rate_limit(request)

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

    if settings.REQUIRE_EMAIL_VERIFICATION:
        code = _create_verification_code(body.email, "email_verify")
        send_verification_email(body.email, code, settings.FRONTEND_URL)
        return {"status": "verification_sent", "message": "Check your email for a verification link."}

    user = user_repo.update_user(user["id"], email_verified=True)
    token = create_token(user["id"], user["email"], settings.JWT_SECRET)
    return {"status": "ok", "token": token, "user": user}


# ── Verify Email ─────────────────────────────────────────────────

@router.post("/verify-email")
def verify_email(body: VerifyEmailRequest):
    if not _verify_code(body.email, body.code, "email_verify"):
        raise HTTPException(400, "Invalid or expired verification code")

    user = user_repo.get_user_by_email(body.email)
    if not user:
        raise HTTPException(404, "User not found")

    user = user_repo.update_user(user["id"], email_verified=True)
    token = create_token(user["id"], user["email"], settings.JWT_SECRET)
    return {"status": "email_verified", "token": token, "user": user}


# ── Login ────────────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, request: Request):
    _check_rate_limit(request)

    try:
        user_dict = user_repo.get_user_by_email_with_password(body.email)
    except Exception as e:
        logger.error(f"Login lookup failed: {e}", exc_info=True)
        raise HTTPException(500, "Login temporarily unavailable")

    if not user_dict:
        raise HTTPException(401, "Invalid email or password")

    if not user_dict.get("password"):
        raise HTTPException(401, "This account uses Google sign-in")

    if not verify_password(body.password, user_dict["password"]):
        raise HTTPException(401, "Invalid email or password")

    if settings.REQUIRE_EMAIL_VERIFICATION and not user_dict.get("email_verified"):
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

    try:
        google_user = await verify_google_token(body.id_token, settings.GOOGLE_OAUTH_CLIENT_ID)
    except Exception as e:
        logger.error(f"Google token verification failed: {e}", exc_info=True)
        raise HTTPException(500, "Google sign-in temporarily unavailable")

    if not google_user:
        raise HTTPException(401, "Invalid Google token")

    try:
        existing = user_repo.get_user_by_email(google_user["email"])
        if existing:
            if not existing.get("email_verified"):
                user_repo.update_user(existing["id"], email_verified=True)
            user = user_repo.get_user_by_email(google_user["email"])
        else:
            user = user_repo.create_user(
                email=google_user["email"],
                name=google_user["name"],
                auth_provider="google",
                avatar_url=google_user.get("picture"),
            )
            user = user_repo.update_user(user["id"], email_verified=True)
    except Exception as e:
        logger.error(f"Google auth user creation failed: {e}", exc_info=True)
        raise HTTPException(500, "Google sign-in failed — please try again")

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
    user_repo.update_user(user["id"], password=hashed)

    return {"status": "password_reset"}


# ── Profile ──────────────────────────────────────────────────────

@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.patch("/profile")
def update_profile(body: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    if not body.name:
        raise HTTPException(400, "Nothing to update")
    return user_repo.update_user(user["id"], name=body.name)


class UpdateLlmSettingsRequest(BaseModel):
    llm_provider: Optional[str] = None  # "gemini" | "openrouter" | "ollama" | None (use global default)
    llm_model: Optional[str] = None


@router.patch("/llm-settings")
def update_llm_settings(body: UpdateLlmSettingsRequest, user: dict = Depends(get_current_user)):
    valid_providers = {"gemini", "openrouter", "ollama", None, ""}
    if body.llm_provider not in valid_providers and body.llm_provider is not None:
        raise HTTPException(400, f"Invalid provider. Use one of: gemini, openrouter, ollama")

    # Empty string means "reset to global default"
    provider = body.llm_provider or None
    model = body.llm_model or None
    return user_repo.update_user(user["id"], llm_provider=provider, llm_model=model)


@router.get("/llm-settings/available")
def available_llm_settings():
    from llm.factory import AVAILABLE_MODELS
    from configs.config import settings
    return {
        "models": AVAILABLE_MODELS,
        "global_default_provider": settings.LLM_PROVIDER,
        "providers_configured": {
            "gemini": bool(settings.GOOGLE_API_KEY),
            "openrouter": bool(settings.OPENROUTER_API_KEY),
            "ollama": True,  # always shown as an option; actual availability depends on local server
        },
    }


@router.post("/change-password")
def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    user_data = user_repo.get_user_by_email_with_password(user["email"])
    if not user_data:
        raise HTTPException(404, "User not found")

    if user_data.get("auth_provider") == "google" and not user_data.get("password"):
        hashed = hash_password(body.new_password)
        user_repo.update_user(user["id"], password=hashed)
        return {"status": "password_set"}

    if not user_data.get("password"):
        raise HTTPException(400, "No password set")

    if not verify_password(body.current_password, user_data["password"]):
        raise HTTPException(401, "Current password is incorrect")

    hashed = hash_password(body.new_password)
    user_repo.update_user(user["id"], password=hashed)
    return {"status": "password_changed"}
