"""Database backend factory.

To add a new backend:
1. Create storage/backends/mydb/ with the 5 repo modules
2. Add an elif here
3. Set DB_BACKEND=mydb in .env
"""

from storage.backends.base import StorageBackend

_backend: StorageBackend | None = None


def get_backend() -> StorageBackend:
    global _backend
    if _backend is not None:
        return _backend

    from configs.config import settings
    backend_name = settings.DB_BACKEND.lower()

    if backend_name == "supabase":
        from storage.backends.supabase import create_backend
        _backend = create_backend()
    elif backend_name == "sqlite":
        from storage.backends.sqlite import create_backend
        _backend = create_backend()
    # elif backend_name == "postgres":
    #     from storage.backends.postgres import create_backend
    #     _backend = create_backend()
    # elif backend_name == "mongodb":
    #     from storage.backends.mongodb import create_backend
    #     _backend = create_backend()
    else:
        raise ValueError(f"Unknown DB_BACKEND: {backend_name}. Use 'sqlite' or 'supabase'.")

    return _backend


def reset_backend():
    global _backend
    _backend = None
