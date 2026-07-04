"""Thin wrapper around the Anthropic Messages API."""

from typing import AsyncIterator

import anthropic

from llm.prompts import SYSTEM_PROMPT

_DEFAULT_MODEL = "claude-haiku-4-5"
_MAX_TOKENS = 2048

KNOWN_MODELS = ["claude-haiku-4-5"]


class AnthropicClient:
    def __init__(self, api_key: str, model: str | None = None):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._async_client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model or _DEFAULT_MODEL

    # ── Synchronous (blocking) ────────────────────────────────────

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        format: str | dict | None = None,
    ) -> str:
        msgs = self._convert_messages(messages)
        resp = self._client.messages.create(
            model=model or self.model,
            max_tokens=_MAX_TOKENS,
            system=system or SYSTEM_PROMPT,
            messages=msgs,
        )
        return resp.content[0].text

    def generate(self, prompt: str, model: str | None = None, system: str | None = None) -> str:
        resp = self._client.messages.create(
            model=model or self.model,
            max_tokens=_MAX_TOKENS,
            system=system or SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text

    # ── Async streaming ───────────────────────────────────────────

    async def chat_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        format: str | dict | None = None,
    ) -> AsyncIterator[str]:
        msgs = self._convert_messages(messages)
        async with self._async_client.messages.stream(
            model=model or self.model,
            max_tokens=_MAX_TOKENS,
            system=system or SYSTEM_PROMPT,
            messages=msgs,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def chat_full_async(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        format: str | dict | None = None,
    ) -> str:
        msgs = self._convert_messages(messages)
        resp = await self._async_client.messages.create(
            model=model or self.model,
            max_tokens=_MAX_TOKENS,
            system=system or SYSTEM_PROMPT,
            messages=msgs,
        )
        return resp.content[0].text

    # ── Helpers ────────────────────────────────────────────────────

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        """Strip system messages (passed separately) and map roles."""
        result = []
        for m in messages:
            role = m.get("role", "")
            if role == "system":
                continue
            # Anthropic uses "user" and "assistant"
            anthropic_role = "assistant" if role in ("assistant", "agent") else "user"
            result.append({"role": anthropic_role, "content": m.get("content", "")})
        return result
