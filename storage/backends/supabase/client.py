"""Supabase client singleton."""

_client = None


def get_supabase():
    global _client
    if _client is not None:
        return _client

    from configs.config import settings
    from supabase import create_client
    _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client
