"""Returns the configured LLM client — Gemini, OpenRouter, or Ollama.

Supports per-user overrides (provider/model) on top of the global default,
so each user can pick their own model in Settings without redeploying.
"""

_clients_cache: dict[str, object] = {}


def get_llm_client(provider: str | None = None, model: str | None = None):
    """Get an LLM client. If provider/model are omitted, falls back to global config."""
    from configs.config import settings

    provider = (provider or settings.LLM_PROVIDER).lower()
    cache_key = f"{provider}:{model or ''}"

    if cache_key in _clients_cache:
        return _clients_cache[cache_key]

    if provider == "gemini" and settings.GOOGLE_API_KEY:
        from llm.gemini_client import GeminiClient
        client = GeminiClient(
            api_key=settings.GOOGLE_API_KEY,
            model=model or settings.GEMINI_MODEL,
        )
    elif provider == "openrouter" and settings.OPENROUTER_API_KEY:
        from llm.openrouter_client import OpenRouterClient
        client = OpenRouterClient(
            api_key=settings.OPENROUTER_API_KEY,
            model=model or settings.OPENROUTER_MODEL,
        )
    elif provider == "ollama":
        from llm.ollama_client import OllamaClient
        client = OllamaClient(
            base_url=settings.OLLAMA_BASE_URL,
            model=model or settings.OLLAMA_CHAT_MODEL,
            timeout=settings.OLLAMA_TIMEOUT,
        )
    else:
        # Unknown/misconfigured provider — fall back to global default provider
        return get_llm_client(provider=settings.LLM_PROVIDER, model=model)

    _clients_cache[cache_key] = client
    return client


def get_llm_client_for_user(user: dict | None):
    """Resolve the LLM client for a specific user, honoring their saved preference."""
    if not user:
        return get_llm_client()
    provider = user.get("llm_provider") or None
    model = user.get("llm_model") or None
    return get_llm_client(provider=provider, model=model)


def reset_client():
    global _clients_cache
    _clients_cache = {}


AVAILABLE_MODELS = {
    "gemini": [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ],
    "openrouter": [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
        "deepseek/deepseek-chat:free",
        "qwen/qwen-2.5-72b-instruct:free",
    ],
    "ollama": [
        "qwen2.5:7b",
        "llama3.1:8b",
        "mistral:7b",
    ],
}
