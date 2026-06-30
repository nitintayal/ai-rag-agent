"""Returns the configured LLM client — Gemini, OpenRouter, or Ollama."""

_client = None


def get_llm_client():
    global _client
    if _client is not None:
        return _client

    from configs.config import settings

    provider = settings.LLM_PROVIDER.lower()

    if provider == "gemini" and settings.GOOGLE_API_KEY:
        from llm.gemini_client import GeminiClient
        _client = GeminiClient(
            api_key=settings.GOOGLE_API_KEY,
            model=settings.GEMINI_MODEL,
        )
    elif provider == "openrouter" and settings.OPENROUTER_API_KEY:
        from llm.openrouter_client import OpenRouterClient
        _client = OpenRouterClient(
            api_key=settings.OPENROUTER_API_KEY,
            model=settings.OPENROUTER_MODEL,
        )
    else:
        from llm.ollama_client import OllamaClient
        _client = OllamaClient(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_CHAT_MODEL,
            timeout=settings.OLLAMA_TIMEOUT,
        )

    return _client


def reset_client():
    global _client
    _client = None
