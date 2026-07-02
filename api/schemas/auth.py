from typing import Optional

from pydantic import BaseModel, Field


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


class UpdateLlmSettingsRequest(BaseModel):
    llm_provider: Optional[str] = None  # "gemini" | "openrouter" | "ollama" | None (use global default)
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None   # user's own API key; "" means clear it
