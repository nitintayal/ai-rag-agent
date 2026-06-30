"""OpenRouter client — OpenAI-compatible API, access to many models (including free ones) via one key."""

import json
import logging
from typing import AsyncIterator

import httpx

from llm.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
_DEFAULT_TIMEOUT = 60


class OpenRouterClient:
    def __init__(self, api_key: str, model: str | None = None, timeout: int | None = None):
        self.api_key = api_key
        self.model = model or _DEFAULT_MODEL
        self.timeout = timeout or _DEFAULT_TIMEOUT

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # OpenRouter uses these for their public leaderboard / rate-limit fairness — optional but good practice
            "HTTP-Referer": "https://iassistant.in",
            "X-Title": "AI Personal Assistant",
        }

    def _build_messages(self, messages: list[dict], system: str | None) -> list[dict]:
        msgs = list(messages)
        sys_content = system or SYSTEM_PROMPT
        if sys_content and (not msgs or msgs[0].get("role") != "system"):
            msgs.insert(0, {"role": "system", "content": sys_content})
        return msgs

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        format: str | dict | None = None,
    ) -> str:
        payload = {
            "model": model or self.model,
            "messages": self._build_messages(messages, system),
            "temperature": 0.3,
        }
        if format == "json":
            payload["response_format"] = {"type": "json_object"}

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{_BASE_URL}/chat/completions", json=payload, headers=self._headers())
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

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
            "model": model or self.model,
            "messages": self._build_messages(messages, system),
            "temperature": 0.3,
            "stream": True,
        }
        if format == "json":
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=10)) as client:
            async with client.stream(
                "POST", f"{_BASE_URL}/chat/completions", json=payload, headers=self._headers()
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

    async def chat_full_async(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        format: str | dict | None = None,
    ) -> str:
        return self.chat(messages, model, system, format)
