from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Literal, TypedDict, Tuple

from configs.config import settings
from langchain_core.language_models.chat_models import SimpleChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class ModelConfig(TypedDict, total=False):
    model_name: str
    provider: str
    api_key: str
    temperature: float
    max_new_tokens: int
    device: str
    response_format: str


def get_agent_mode() -> AgentMode:
    mode = settings.AGENT_MODE.strip().lower()
    if mode not in {"legacy", "deep"}:
        raise ValueError("AGENT_MODE must be either 'legacy' or 'deep'")
    return mode


def get_environment_model_settings() -> dict[str, str]:
    return {
        "agent_mode": get_agent_mode(),
        "llm_model": settings.LLM_MODEL,
        "deep_agent_model": settings.DEEP_AGENT_MODEL,
        "router_model": settings.ROUTER_MODEL,
        "google_api_key": settings.GOOGLE_API_KEY,
    }


def build_model_config(model_type: ModelType) -> ModelConfig:
    if model_type == "llm":
        return {
            "model_name": settings.LLM_MODEL,
            "provider": "hf",
            "temperature": 0.0,
            "max_new_tokens": 300,
            "device": "cpu",
        }

    if model_type == "deep_agent":
        if settings.GOOGLE_API_KEY:
            return {
                "model_name": settings.DEEP_AGENT_MODEL,
                "provider": "google_genai",
                "api_key": settings.GOOGLE_API_KEY,
                "temperature": 0.0,
            }
        return {
            "model_name": settings.LLM_MODEL,
            "provider": "hf",
            "temperature": 0.0,
            "max_new_tokens": 300,
            "device": "cpu",
        }

    if model_type == "router":
        return {
            "model_name": settings.ROUTER_MODEL,
            "provider": "google_genai",
            "api_key": settings.GOOGLE_API_KEY,
            "temperature": 0.0,
            "response_format": "json",
        }

    raise ValueError(
        f"Unsupported model type '{model_type}'. Must be one of: llm, deep_agent, router."
    )


class HFChatModel(SimpleChatModel):
    """Minimal LangChain-compatible chat model wrapper for local Hugging Face models."""

    model_name: str
    tokenizer: Any
    model: Any
    provider: str = "hf"
    temperature: float = 0.0
    max_new_tokens: int = 300
    bound_tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_choice: str | None = None

    @property
    def _llm_type(self) -> str:
        return self.provider

    def _get_ls_params(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "ls_provider": self.provider,
            "provider": self.provider,
            "model_name": self.model_name,
        }

    def bind_tools(
        self,
        tools: list[Any],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Any:
        from langchain_core.utils.function_calling import convert_to_openai_tool

        formatted_tools = [convert_to_openai_tool(tool) for tool in tools]
        return self.model_copy(
            update={
                "bound_tools": formatted_tools,
                "tool_choice": tool_choice,
            }
        )

    def _messages_to_prompt(self, messages: list[Any]) -> str:
        prompt_parts: list[str] = []
        for message in messages:
            role = getattr(message, "role", "user")
            content = getattr(message, "content", "")
            if isinstance(content, list):
                content = "\n".join(
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict)
                )
            prompt_parts.append(f"{role.capitalize()}: {content}")

        if self.bound_tools:
            tool_lines = []
            for tool in self.bound_tools:
                function_spec = tool.get("function", {}) if isinstance(tool, dict) else {}
                name = function_spec.get("name", "tool")
                description = function_spec.get("description", "")
                tool_lines.append(f"- {name}: {description}".strip())
            prompt_parts.append(
                "Available tools:\n" + "\n".join(tool_lines)
            )
            prompt_parts.append(
                "If a tool is appropriate, reply with a JSON object of the form "
                '{"tool_calls":[{"name":"tool_name","arguments":{...}}]}'
            )

        prompt_parts.append("Assistant:")
        return "\n".join(prompt_parts)

    def _parse_tool_calls(self, output_text: str) -> list[dict[str, Any]]:
        if not self.bound_tools:
            return []

        stripped = output_text.strip()
        if not stripped:
            return []

        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return []

        if isinstance(payload, dict):
            if isinstance(payload.get("tool_calls"), list):
                tool_calls = []
                for item in payload["tool_calls"]:
                    if not isinstance(item, dict):
                        continue
                    name = item.get("name") or item.get("function", {}).get("name")
                    arguments = item.get("arguments") or item.get("args") or {}
                    if name:
                        tool_calls.append({"name": name, "args": arguments})
                return tool_calls

            if "name" in payload:
                return [{"name": payload["name"], "args": payload.get("arguments") or payload.get("args") or {}}]

        return []

    def _call(self, messages: list[Any], stop: list[str] | None = None, **kwargs: Any) -> str:
        prompt = self._messages_to_prompt(messages)
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True)
        inputs = inputs.to(self.model.device)

        generation_kwargs: dict[str, Any] = {
            "max_new_tokens": self.max_new_tokens,
            "do_sample": self.temperature > 0,
            "temperature": float(self.temperature),
        }

        output = self.model.generate(**inputs, **generation_kwargs)
        generated_tokens = output[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(generated_tokens, skip_special_tokens=True)

    def _generate(
        self,
        messages: list[Any],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        output_text = self._call(messages, stop=stop, run_manager=run_manager, **kwargs)
        tool_calls = self._parse_tool_calls(output_text)
        if tool_calls:
            message = AIMessage(content="", tool_calls=tool_calls)
        else:
            message = AIMessage(content=output_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])


@lru_cache(maxsize=1)
def load_llm_components() -> Tuple[Any, Any]:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch

    llm_config = build_model_config("llm")
    tokenizer = AutoTokenizer.from_pretrained(llm_config["model_name"])
    model = AutoModelForCausalLM.from_pretrained(
        llm_config["model_name"],
        device_map=llm_config["device"],
        dtype=torch.float32,
    )
    return tokenizer, model


@lru_cache(maxsize=1)
def load_deep_agent_model() -> Any:
    deep_config = build_model_config("deep_agent")
    if deep_config["provider"] == "google_genai":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=deep_config["model_name"],
            api_key=deep_config["api_key"],
            temperature=deep_config["temperature"],
        )

    tokenizer, model = load_llm_components()
    return HFChatModel(
        model_name=deep_config["model_name"],
        tokenizer=tokenizer,
        model=model,
        temperature=deep_config.get("temperature", 0.0),
        max_new_tokens=deep_config.get("max_new_tokens", 300),
    )


@lru_cache(maxsize=1)
def load_router_client() -> Any:
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is not installed. Install requirements to enable router model use."
        ) from exc

    router_config = build_model_config("router")
    return genai.Client(api_key=router_config["api_key"])


@lru_cache(maxsize=1)
def load_model(model_type: ModelType) -> Any:
    if model_type == "llm":
        return load_llm_components()
    if model_type == "deep_agent":
        return load_deep_agent_model()
    if model_type == "router":
        return load_router_client()
    raise ValueError(
        f"Unsupported model type '{model_type}'. Must be one of: llm, deep_agent, router."
    )


def get_active_model_config() -> ModelConfig:
    mode = get_agent_mode()
    if mode == "deep":
        return build_model_config("deep_agent")
    return build_model_config("llm")


def get_active_model_name() -> str:
    return get_active_model_config()["model_name"]
