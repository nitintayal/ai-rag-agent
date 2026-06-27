"""Thin wrapper around the Ollama REST API (/api/chat, /api/generate)."""

import json
from typing import AsyncIterator

import httpx

from llm.prompts import SYSTEM_PROMPT

_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_MODEL = "qwen2.5:7b"
_DEFAULT_TIMEOUT = 120


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ):
        self.base_url = (base_url or _DEFAULT_BASE_URL).rstrip("/")
        self.model = model or _DEFAULT_MODEL
        self.timeout = timeout or _DEFAULT_TIMEOUT

    # ── Synchronous (blocking) ────────────────────────────────────

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        format: str | dict | None = None,
    ) -> str:
        """Send a chat request and return the full response text."""
        payload = self._build_payload(messages, model, system, format, stream=False)
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    def generate(self, prompt: str, model: str | None = None, system: str | None = None) -> str:
        """Raw generate (no chat format). Useful for simple completions."""
        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json()["response"]

    # ── Async streaming ───────────────────────────────────────────

    async def chat_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        format: str | dict | None = None,
    ) -> AsyncIterator[str]:
        """Stream tokens from Ollama /api/chat. Yields text chunks as they arrive."""
        payload = self._build_payload(messages, model, system, format, stream=True)
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=10)) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    if chunk.get("done"):
                        break
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token

    async def chat_full_async(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        format: str | dict | None = None,
    ) -> str:
        """Async non-streaming chat. Returns the full response text."""
        payload = self._build_payload(messages, model, system, format, stream=False)
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=10)) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    # ── Helpers ────────────────────────────────────────────────────

    def _build_payload(
        self,
        messages: list[dict],
        model: str | None,
        system: str | None,
        format: str | dict | None,
        stream: bool,
    ) -> dict:
        msgs = list(messages)
        sys_content = system or SYSTEM_PROMPT
        if sys_content and (not msgs or msgs[0].get("role") != "system"):
            msgs.insert(0, {"role": "system", "content": sys_content})

        payload: dict = {
            "model": model or self.model,
            "messages": msgs,
            "stream": stream,
            "options": {
                "temperature": 0.3,
                "num_predict": 2048,
            },
        }
        if format:
            payload["format"] = format
        return payload
