"""Gemini API client — drop-in alternative to OllamaClient."""

import json
import time
import logging
from typing import AsyncIterator

from google import genai

from llm.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
MAX_RETRIES = 2
RETRY_DELAY = 2


def _is_quota_exhausted(error: Exception | None) -> bool:
    """Daily quota errors shouldn't be retried — they won't recover within seconds."""
    if error is None:
        return False
    err_str = str(error)
    return "RESOURCE_EXHAUSTED" in err_str or "PerDay" in err_str or "FreeTier" in err_str


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.model = model
        self.client = genai.Client(api_key=api_key)

    def _call_with_retry(self, fn, **kwargs):
        models_to_try = [kwargs.pop("model", None) or self.model]
        for fb in FALLBACK_MODELS:
            if fb not in models_to_try:
                models_to_try.append(fb)

        last_error = None
        for model in models_to_try:
            # Daily quota exhausted — retrying the same model is pointless, skip straight to next
            if _is_quota_exhausted(last_error):
                logger.warning(f"Skipping retries, daily quota exhausted — trying {model}")
                try:
                    return fn(model=model, **kwargs)
                except Exception as e:
                    last_error = e
                    continue

            for attempt in range(MAX_RETRIES):
                try:
                    return fn(model=model, **kwargs)
                except Exception as e:
                    last_error = e
                    if _is_quota_exhausted(e):
                        logger.warning(f"{model} daily quota exhausted, moving to next model")
                        break
                    err_str = str(e)
                    if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                        logger.warning(f"{model} attempt {attempt+1} failed: {e}")
                        time.sleep(RETRY_DELAY * (attempt + 1))
                        continue
                    raise
        raise last_error

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

        def _do(model, **kw):
            response = self.client.models.generate_content(
                model=model, contents=contents, config=config,
            )
            return response.text

        return self._call_with_retry(_do, model=model)

    def generate(self, prompt: str, model: str | None = None, system: str | None = None) -> str:
        config = {}
        if system:
            config["system_instruction"] = system

        def _do(model, **kw):
            response = self.client.models.generate_content(
                model=model, contents=prompt, config=config,
            )
            return response.text

        return self._call_with_retry(_do, model=model)

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

        models_to_try = [model or self.model] + [m for m in FALLBACK_MODELS if m != (model or self.model)]
        last_error = None
        for m in models_to_try:
            try:
                response = self.client.models.generate_content_stream(
                    model=m, contents=contents, config=config,
                )
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as e:
                last_error = e
                if _is_quota_exhausted(e):
                    logger.warning(f"Stream {m} daily quota exhausted, trying next model")
                    continue
                if "503" in str(e) or "UNAVAILABLE" in str(e) or "429" in str(e):
                    logger.warning(f"Stream {m} unavailable, trying next: {e}")
                    continue
                raise
        if last_error:
            yield f"\n\n[All Gemini models exhausted their free quota for today. Error: {last_error}]"

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
