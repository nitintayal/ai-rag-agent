"""OpenRouter client — OpenAI-compatible API, access to many models (including free ones) via one key."""

import json
import logging
import time
from typing import AsyncIterator

import httpx

from llm.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
_DEFAULT_TIMEOUT = 60

# Other free models to fall back to if the primary one is rate-limited.
# Each :free model on OpenRouter has its own independent rate-limit pool.
_FALLBACK_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "deepseek/deepseek-chat:free",
    "qwen/qwen-2.5-72b-instruct:free",
]
_MAX_RETRIES = 2
_RETRY_DELAY = 2


def _should_try_next_model(error: Exception) -> bool:
    """429 (rate limited) or 404 (model deprecated/renamed) — both mean 'skip to next model'."""
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code in (404, 429)
    msg = str(error).lower()
    return "429" in msg or "404" in msg or "rate limit" in msg or "not found" in msg


def _is_invalid_model(error: Exception) -> bool:
    """404 means the model ID itself is bad — no point retrying the same model."""
    return isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 404


class OpenRouterClient:
    def __init__(self, api_key: str, model: str | None = None, timeout: int | None = None):
        self.api_key = api_key
        self.model = model or _DEFAULT_MODEL
        self.timeout = timeout or _DEFAULT_TIMEOUT

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://iassistant.in",
            "X-Title": "AI Personal Assistant",
        }

    def _build_messages(self, messages: list[dict], system: str | None) -> list[dict]:
        msgs = list(messages)
        sys_content = system or SYSTEM_PROMPT
        if sys_content and (not msgs or msgs[0].get("role") != "system"):
            msgs.insert(0, {"role": "system", "content": sys_content})
        return msgs

    def _models_to_try(self, model: str | None) -> list[str]:
        primary = model or self.model
        rest = [m for m in _FALLBACK_MODELS if m != primary]
        return [primary] + rest

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        format: str | dict | None = None,
    ) -> str:
        payload = {
            "messages": self._build_messages(messages, system),
            "temperature": 0.3,
        }
        if format == "json":
            payload["response_format"] = {"type": "json_object"}

        last_error = None
        for m in self._models_to_try(model):
            for attempt in range(_MAX_RETRIES):
                try:
                    with httpx.Client(timeout=self.timeout) as client:
                        resp = client.post(
                            f"{_BASE_URL}/chat/completions",
                            json={**payload, "model": m},
                            headers=self._headers(),
                        )
                        resp.raise_for_status()
                        return resp.json()["choices"][0]["message"]["content"]
                except Exception as e:
                    last_error = e
                    if _is_invalid_model(e):
                        logger.warning(f"OpenRouter model '{m}' not found (404) — likely deprecated/renamed, trying next model")
                        break  # no point retrying a nonexistent model
                    if _should_try_next_model(e):
                        logger.warning(f"OpenRouter {m} rate-limited (attempt {attempt+1}): {e}")
                        if attempt < _MAX_RETRIES - 1:
                            time.sleep(_RETRY_DELAY)
                        continue
                    raise
            else:
                logger.warning(f"OpenRouter {m} exhausted retries, trying next model")
        raise last_error

    def generate(self, prompt: str, model: str | None = None, system: str | None = None) -> str:
        return self.chat([{"role": "user", "content": prompt}], model=model, system=system)

    async def chat_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        format: str | dict | None = None,
    ) -> AsyncIterator[str]:
        payload = {
            "messages": self._build_messages(messages, system),
            "temperature": 0.3,
            "stream": True,
        }
        if format == "json":
            payload["response_format"] = {"type": "json_object"}

        last_error = None
        for m in self._models_to_try(model):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=10)) as client:
                    async with client.stream(
                        "POST", f"{_BASE_URL}/chat/completions",
                        json={**payload, "model": m}, headers=self._headers(),
                    ) as resp:
                        resp.raise_for_status()
                        async for line in resp.aiter_lines():
                            if not line.strip() or not line.startswith("data: "):
                                continue
                            data = line[len("data: "):].strip()
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                            except json.JSONDecodeError:
                                continue
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield token
                return
            except Exception as e:
                last_error = e
                if _should_try_next_model(e):
                    logger.warning(f"OpenRouter stream {m} rate-limited, trying next model: {e}")
                    continue
                raise
        if last_error:
            yield f"\n\n[All OpenRouter free models are rate-limited right now. Try again shortly, or switch provider in Settings. Error: {last_error}]"

    async def chat_full_async(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        format: str | dict | None = None,
    ) -> str:
        return self.chat(messages, model, system, format)
