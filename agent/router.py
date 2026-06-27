from typing import Literal

from pydantic import BaseModel, Field

from configs.config import settings
from .model import build_model_config, load_model


class ToolDecision(BaseModel):
    tool: Literal["web", "rag"] = Field(
        description="Select 'web' for fresh external information, otherwise 'rag' for internal knowledge base questions."
    )


def keyword_fallback_router(question: str) -> str:
    query = question.lower()
    web_keywords = (
        "latest",
        "current",
        "today",
        "recent",
        "news",
        "trending",
        "weather",
        "stock price",
        "sports score",
        "live",
        "breaking",
        "update",
    )
    return "web" if any(keyword in query for keyword in web_keywords) else "rag"


def gemini_structured_router(question: str) -> str:
    if not settings.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is not configured")

    router_config = build_model_config("router")

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is not installed. Install requirements to enable structured routing."
        ) from exc

    prompt = f"""
You are a routing classifier for a RAG agent.
Return JSON that matches the provided schema.

Choose:
- web: for fresh, current, external, public-web, or time-sensitive information
- rag: for questions that should be answered from the local/internal knowledge base

Question: {question}
""".strip()

    client = load_model("router")
    response = client.models.generate_content(
        model=router_config["model_name"],
        contents=prompt,
        config={
            "temperature": 0,
            "response_mime_type": "application/json",
            "response_json_schema": ToolDecision.model_json_schema(),
        },
    )

    decision = ToolDecision.model_validate_json(response.text)
    return decision.tool
