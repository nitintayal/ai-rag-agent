"""Auth routes: register, login, Google OAuth, email verification, password reset.

For account-management routes (profile, change-password, LLM settings), see api/routes/profile.py.
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from auth.passwords import hash_password, verify_password
from auth.jwt_utils import create_token
from auth.google_oauth import verify_google_token
from auth.email import send_verification_email, send_password_reset_email
from auth.rate_limit import check_rate_limit
from auth.verification import create_verification_code, verify_code
from api.schemas.auth import (
    RegisterRequest, LoginRequest, GoogleAuthRequest, AuthResponse,
    ForgotPasswordRequest, ResetPasswordRequest, VerifyEmailRequest,
)
from configs.config import settings
from storage.repositories import user_repo

router = APIRouter(prefix="/auth")
logger = logging.getLogger(__name__)


# ── Register ─────────────────────────────────────────────────────

@router.post("/register")
def register(body: RegisterRequest, request: Request):
    check_rate_limit(request)

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
        code = create_verification_code(body.email, "email_verify")
        send_verification_email(body.email, code, settings.FRONTEND_URL)
        return {"status": "verification_sent", "message": "Check your email for a verification link."}

    user = user_repo.update_user(user["id"], email_verified=True)
    token = create_token(user["id"], user["email"], settings.JWT_SECRET)
    return {"status": "ok", "token": token, "user": user}


# ── Verify Email ─────────────────────────────────────────────────

@router.post("/verify-email")
def verify_email(body: VerifyEmailRequest):
    if not verify_code(body.email, body.code, "email_verify"):
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
    check_rate_limit(request)

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
        code = create_verification_code(body.email, "email_verify")
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
            # update_user returns the updated user — no need to re-fetch
            user = user_repo.update_user(existing["id"], email_verified=True)
        else:
            created = user_repo.create_user(
                email=google_user["email"],
                name=google_user["name"],
                auth_provider="google",
                avatar_url=google_user.get("picture"),
            )
            user = user_repo.update_user(created["id"], email_verified=True)
    except Exception as e:
        logger.error(f"Google auth user creation failed: {e}", exc_info=True)
        raise HTTPException(500, "Google sign-in failed — please try again")

    token = create_token(user["id"], user["email"], settings.JWT_SECRET)
    return {"token": token, "user": user}


# ── Forgot / Reset Password ─────────────────────────────────────

@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, request: Request):
    check_rate_limit(request)

    user = user_repo.get_user_by_email(body.email)
    if user:
        code = create_verification_code(body.email, "password_reset")
        send_password_reset_email(body.email, code, settings.FRONTEND_URL)

    return {"message": "If this email exists, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, request: Request):
    check_rate_limit(request)

    if not verify_code(body.email, body.code, "password_reset"):
        raise HTTPException(400, "Invalid or expired reset code")

    user = user_repo.get_user_by_email(body.email)
    if not user:
        raise HTTPException(404, "User not found")

    hashed = hash_password(body.new_password)
    user_repo.update_user(user["id"], password=hashed)

    return {"status": "password_reset"}
