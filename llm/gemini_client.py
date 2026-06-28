"""Gemini API client — drop-in alternative to OllamaClient."""

import json
from typing import AsyncIterator

from google import genai

from llm.prompts import SYSTEM_PROMPT


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.model = model
        self.client = genai.Client(api_key=api_key)

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        format: str | dict | None = None,
    ) -> str:
        sys_content = system or SYSTEM_PROMPT
        contents = self._to_gemini_contents(messages)

        config = {"system_instruction": sys_content}
        if format == "json":
            config["response_mime_type"] = "application/json"

        response = self.client.models.generate_content(
            model=model or self.model,
            contents=contents,
            config=config,
        )
        return response.text

    def generate(self, prompt: str, model: str | None = None, system: str | None = None) -> str:
        config = {}
        if system:
            config["system_instruction"] = system
        response = self.client.models.generate_content(
            model=model or self.model,
            contents=prompt,
            config=config,
        )
        return response.text

    async def chat_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        format: str | dict | None = None,
    ) -> AsyncIterator[str]:
        sys_content = system or SYSTEM_PROMPT
        contents = self._to_gemini_contents(messages)

        config = {"system_instruction": sys_content}
        if format == "json":
            config["response_mime_type"] = "application/json"

        response = self.client.models.generate_content_stream(
            model=model or self.model,
            contents=contents,
            config=config,
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text

    async def chat_full_async(
        self,
        messages: list[dict],
        model: str | None = None,
        system: str | None = None,
        format: str | dict | None = None,
    ) -> str:
        return self.chat(messages, model, system, format)

    @staticmethod
    def _to_gemini_contents(messages: list[dict]) -> list[dict]:
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                continue
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": msg["content"]}]})
        return contents
