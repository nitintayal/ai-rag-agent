"""Check Ollama availability and model status."""

import httpx


def check_ollama_running(base_url: str = "http://localhost:11434") -> bool:
    try:
        resp = httpx.get(f"{base_url}/api/version", timeout=5)
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def list_models(base_url: str = "http://localhost:11434") -> list[str]:
    try:
        resp = httpx.get(f"{base_url}/api/tags", timeout=10)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
        return []


def is_model_available(model: str, base_url: str = "http://localhost:11434") -> bool:
    models = list_models(base_url)
    return any(model in m for m in models)


def pull_model(model: str, base_url: str = "http://localhost:11434") -> bool:
    """Pull a model. Blocks until complete. Returns True on success."""
    try:
        resp = httpx.post(
            f"{base_url}/api/pull",
            json={"name": model, "stream": False},
            timeout=600,
        )
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def get_status(base_url: str = "http://localhost:11434", model: str = "qwen2.5:7b") -> dict:
    running = check_ollama_running(base_url)
    models = list_models(base_url) if running else []
    return {
        "ollama_running": running,
        "available_models": models,
        "target_model_ready": any(model in m for m in models),
        "target_model": model,
    }
