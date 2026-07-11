"""Account management routes: profile, password change, LLM model preference.

Shares the /auth URL prefix with api/routes/auth.py (login/register/etc.) —
split here purely for file organization, not for the API contract.
"""

from fastapi import APIRouter, HTTPException, Depends

from auth.passwords import hash_password, verify_password
from api.dependencies import get_current_user
from api.schemas.auth import UpdateProfileRequest, ChangePasswordRequest, UpdateLlmSettingsRequest
from storage.repositories import user_repo

router = APIRouter(prefix="/auth")

_VALID_LLM_PROVIDERS = {"gemini", "openrouter", "ollama", "anthropic", None, ""}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.patch("/profile")
def update_profile(body: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    if not body.name:
        raise HTTPException(400, "Nothing to update")
    return user_repo.update_user(user["id"], name=body.name)


@router.patch("/llm-settings")
def update_llm_settings(body: UpdateLlmSettingsRequest, user: dict = Depends(get_current_user)):
    if body.llm_provider not in _VALID_LLM_PROVIDERS and body.llm_provider is not None:
        raise HTTPException(400, "Invalid provider. Use one of: gemini, openrouter, ollama, anthropic")
    if body.llm_provider == "anthropic" and not user.get("is_admin"):
        raise HTTPException(403, "Anthropic provider is restricted to admins")

    # Empty string means "reset to global default" / "clear saved key"
    provider = body.llm_provider or None
    model = body.llm_model or None
    # llm_api_key=None means "don't touch it"; ""  means "clear it"
    update_kwargs = dict(llm_provider=provider, llm_model=model)
    if body.llm_api_key is not None:
        update_kwargs["llm_api_key"] = body.llm_api_key or None
    return user_repo.update_user(user["id"], **update_kwargs)


@router.get("/llm-settings/available")
def available_llm_settings(user: dict = Depends(get_current_user)):
    from llm.factory import AVAILABLE_MODELS
    from configs.config import settings
    is_admin = bool(user.get("is_admin"))
    providers_configured = {
        "gemini": bool(settings.GOOGLE_API_KEY),
        "openrouter": bool(settings.OPENROUTER_API_KEY),
        "ollama": True,
    }
    if is_admin:
        providers_configured["anthropic"] = bool(settings.ANTHROPIC_API_KEY)
    models = {k: v for k, v in AVAILABLE_MODELS.items() if k in providers_configured}
    return {
        "models": models,
        "global_default_provider": settings.LLM_PROVIDER,
        "providers_configured": providers_configured,
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
