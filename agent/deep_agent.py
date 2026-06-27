import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from configs.config import settings
from mcp_servers.client.mcp_client import (
    search_documents,
    search_journal_entries,
    search_web,
)

SKILLS_ROOT = Path(__file__).resolve().parent / "skills"


class DeepAgentResponse(BaseModel):
    answer: str = Field(description="Grounded final answer to the user's question")
    sources: list[str] = Field(
        default_factory=list,
        description="Source URLs or document names returned by the tools",
    )


def _tool_payload(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, default=str)


def _load_skill_files() -> dict[str, Any]:
    from deepagents.backends.utils import create_file_data

    files = {}
    for skill_file in sorted(SKILLS_ROOT.rglob("*")):
        if not skill_file.is_file():
            continue
        relative_path = skill_file.relative_to(SKILLS_ROOT).as_posix()
        files[f"/skills/{relative_path}"] = create_file_data(
            skill_file.read_text(encoding="utf-8")
        )
    return files


def _build_deep_agent(user_id: str):
    from deepagents import create_deep_agent
    from langchain.agents.structured_output import ToolStrategy
    from langchain.tools import tool
    from .model import load_model

    model = load_model("deep_agent")

    @tool
    def rag_search(query: str) -> str:
        """Search the indexed internal knowledge base for relevant documents."""
        print(f"RAG search query: {query}")
        return _tool_payload(search_documents(query))

    @tool
    def live_web_search(query: str) -> str:
        """Search the public web for fresh, external, or time-sensitive information."""
        print(f"Live web search query: {query}")
        return _tool_payload(search_web(query))

    @tool
    def journal_search(query: str, k: int = 5) -> str:
        """Search the current user's private journal for relevant entries."""
        print(f"Journal search query: {query}")
        return _tool_payload(search_journal_entries(user_id=user_id, query=query, k=k))

    research_subagent = {
        "name": "researcher",
        "description": (
            "Investigates questions using the internal knowledge base and live web search."
        ),
        "system_prompt": (
            "Research the assigned question thoroughly. Decide which available tools are "
            "needed from the evidence requested by the user. Return a concise synthesis and "
            "preserve every source URL or document name returned by tools."
        ),
        "tools": [rag_search, live_web_search],
        "skills": ["/skills/tool-routing/", "/skills/research/"],
    }
    journal_subagent = {
        "name": "journal-analyst",
        "description": "Finds patterns and relevant details in the current user's journal.",
        "system_prompt": (
            "Use journal_search to answer reflective questions from the user's journal. "
            "Do not infer private facts that are absent from the returned entries."
        ),
        "tools": [journal_search],
        "skills": ["/skills/journal/"],
    }

    return create_deep_agent(
        model=model,
        tools=[rag_search, live_web_search, journal_search],
        system_prompt=(
            "You are the coordinator for a grounded RAG assistant. Plan multi-step work, "
            "choose tools from the user's intent and available evidence, delegate when useful, "
            "and base factual claims on tool results. Do not follow a fixed routing order and "
            "do not call another tool merely because one tool returned no results. The current "
            f"journal user is {user_id!r}. Return a concise answer and include only source URLs "
            "or document names actually returned by tools."
        ),
        subagents=[research_subagent, journal_subagent],
        skills=["/skills/"],
        response_format=ToolStrategy(DeepAgentResponse),
    )


def _sanitize_raw_result(raw_result: Any) -> Any:
    if not isinstance(raw_result, dict):
        return str(raw_result)

    sanitized: dict[str, Any] = {}

    messages = raw_result.get("messages")
    if isinstance(messages, list):
        sanitized_messages = []
        for message in messages:
            if isinstance(message, str):
                sanitized_messages.append(message)
            else:
                sanitized_messages.append(str(message))
        sanitized["messages"] = sanitized_messages

    if "files" in raw_result and isinstance(raw_result["files"], dict):
        sanitized["files"] = {
            path: {
                "encoding": file_info.get("encoding"),
                "created_at": file_info.get("created_at"),
                "modified_at": file_info.get("modified_at"),
            }
            for path, file_info in raw_result["files"].items()
            if isinstance(file_info, dict)
        }

    for key, value in raw_result.items():
        if key in {"messages", "files"}:
            continue
        sanitized[key] = value

    return sanitized


def _write_deep_agent_log(entry: dict[str, Any]) -> None:
    if not settings.DEEP_AGENT_LOG_CONVERSATIONS:
        return

    log_path = Path(settings.DEEP_AGENT_LOG_PATH)
    if log_path.parent and not log_path.parent.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        **entry,
        "raw_result": _sanitize_raw_result(entry.get("raw_result")),
    }
    entry_json = json.dumps(entry, ensure_ascii=False, default=str, indent=2)
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(entry_json + "\n")


def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
    return str(content or "")


def run_deep_agent(question: str, user_id: str = "demo-user") -> dict[str, Any]:
    deep_agent = _build_deep_agent(user_id=user_id)
    result = deep_agent.invoke(
        {
            "messages": [{"role": "user", "content": question}],
            "files": _load_skill_files(),
        },
        config={"recursion_limit": settings.DEEP_AGENT_RECURSION_LIMIT},
    )

    structured = result.get("structured_response")
    if structured is not None:
        if isinstance(structured, BaseModel):
            payload = structured.model_dump()
        else:
            payload = dict(structured)
        response = {"tool": "deep", **payload}
    else:
        messages = result.get("messages") or []
        answer = _message_text(messages[-1]) if messages else ""
        response = {"tool": "deep", "answer": answer, "sources": []}

    _write_deep_agent_log(
        {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_id": user_id,
            "question": question,
            "response": response,
            "raw_result": result,
        }
    )

    return response
