"""Admin-only routes."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.dependencies import require_admin
from storage.repositories import user_repo

router = APIRouter(prefix="/admin", tags=["admin"])

_VALID_BACKENDS = {"sqlite", "supabase"}


class PromoteRequest(BaseModel):
    email: str
    is_admin: bool = True


class SwitchDbRequest(BaseModel):
    backend: str  # "sqlite" or "supabase"


@router.get("/users")
def list_users(admin: dict = Depends(require_admin)):
    return user_repo.list_users()


@router.post("/promote")
def promote_user(body: PromoteRequest, admin: dict = Depends(require_admin)):
    user = user_repo.get_user_by_email(body.email)
    if not user:
        raise HTTPException(404, "User not found")
    user_repo.update_user(user["id"], is_admin=body.is_admin)
    return {"ok": True, "email": body.email, "is_admin": body.is_admin}


@router.get("/db-status")
def db_status(admin: dict = Depends(require_admin)):
    from configs.config import settings
    return {"current_backend": settings.DB_BACKEND}


@router.post("/switch-db")
def switch_db(body: SwitchDbRequest, admin: dict = Depends(require_admin)):
    if body.backend not in _VALID_BACKENDS:
        raise HTTPException(400, f"Invalid backend. Use one of: {', '.join(_VALID_BACKENDS)}")

    from configs.config import settings
    if settings.DB_BACKEND == body.backend:
        return {"ok": True, "backend": body.backend, "message": "Already using this backend"}

    if body.backend == "supabase" and not (settings.SUPABASE_URL and settings.SUPABASE_KEY):
        raise HTTPException(400, "SUPABASE_URL and SUPABASE_KEY are not configured")

    # Switch in memory
    settings.DB_BACKEND = body.backend
    from storage.factory import reset_backend
    reset_backend()

    # Persist so it survives restarts (on non-ephemeral disks)
    from storage.runtime_config import save as _save_runtime
    _save_runtime("DB_BACKEND", body.backend)

    return {"ok": True, "backend": body.backend, "message": f"Switched to {body.backend}"}


@router.get("/export-db")
def export_db(admin: dict = Depends(require_admin)):
    """Export all data as a portable SQLite file, regardless of active backend."""
    from storage.exporter import export_to_sqlite
    from configs.config import settings
    from datetime import datetime

    try:
        path = export_to_sqlite()
    except Exception as e:
        raise HTTPException(500, f"Export failed: {e}")

    filename = f"assistant_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
    return FileResponse(
        path=path,
        media_type="application/octet-stream",
        filename=filename,
        background=None,
    )
