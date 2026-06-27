"""Graph node functions for the agent."""

import json
import logging

from agent.state import AgentState
from llm.ollama_client import OllamaClient
from llm.prompts import ROUTER_PROMPT, ANSWER_PROMPT, WEB_ANSWER_PROMPT
from memory.context_builder import build_messages
from memory.conversation_memory import ConversationMemory
from memory.long_term_memory import UserMemory
from tools.registry import get_tool

logger = logging.getLogger(__name__)

_KEYWORD_WEB_TRIGGERS = {"latest", "current", "today", "news", "weather", "stock", "price", "now", "recent"}


def _get_llm() -> OllamaClient:
    from configs.config import settings
    return OllamaClient(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_CHAT_MODEL,
        timeout=settings.OLLAMA_TIMEOUT,
    )


def _keyword_fallback_route(question: str) -> str:
    q = question.lower()
    if any(w in q for w in _KEYWORD_WEB_TRIGGERS):
        return "web"
    if any(w in q for w in ("journal", "diary", "note", "reflect")):
        return "journal"
    if any(w in q for w in ("task", "todo", "remind", "deadline")):
        return "task"
    if any(w in q for w in ("remember", "preference", "my name", "i am", "i like", "i prefer")):
        return "memory"
    if any(w in q for w in ("calendar", "event", "meeting", "schedule", "appointment")):
        return "calendar"
    return "direct"


# ── Node: route ──────────────────────────────────────────────────

def route(state: AgentState) -> dict:
    """Decide which tool to use. Tries LLM routing, falls back to keywords."""
    question = state["question"]
    llm = _get_llm()

    try:
        prompt = ROUTER_PROMPT.format(question=question)
        result = llm.chat(
            [{"role": "user", "content": prompt}],
            system="You are a router. Respond only with valid JSON.",
            format="json",
        )
        parsed = json.loads(result)
        tool = parsed.get("tool", "direct")
        if tool in ("rag", "web", "journal", "task", "memory", "calendar", "direct"):
            logger.info(f"LLM routed to: {tool} (reason: {parsed.get('reason', '')})")
            return {"tool": tool}
    except Exception as e:
        logger.debug(f"LLM routing failed, using keyword fallback: {e}")

    tool = _keyword_fallback_route(question)
    logger.info(f"Keyword routed to: {tool}")
    return {"tool": tool}


# ── Node: execute_tool ───────────────────────────────────────────

def execute_tool(state: AgentState) -> dict:
    """Execute the selected tool."""
    tool_name = state.get("tool", "direct")
    if tool_name == "direct":
        return {"context": "", "sources": []}

    tool = get_tool(tool_name)
    if not tool:
        logger.warning(f"Unknown tool: {tool_name}")
        return {"context": "", "sources": []}

    result = tool.execute(
        user_id=state["user_id"],
        query=state["question"],
        **(state.get("tool_args") or {}),
    )

    if result.error:
        logger.error(f"Tool {tool_name} error: {result.error}")
        return {"context": f"Tool error: {result.error}", "sources": []}

    return {"context": result.context, "sources": result.sources or []}


# ── Node: generate ───────────────────────────────────────────────

def generate(state: AgentState) -> dict:
    """Generate the final answer using context + conversation history."""
    question = state["question"]
    context = state.get("context", "")
    tool = state.get("tool", "direct")
    user_id = state["user_id"]
    conversation_id = state["conversation_id"]

    llm = _get_llm()

    # Load conversation memory
    conv_memory = ConversationMemory(conversation_id, user_id)
    user_memory = UserMemory(user_id)

    history = conv_memory.get_history()
    profile_context = user_memory.get_profile_context()

    # Build the prompt based on tool type
    if tool == "web" and context:
        answer_prompt = WEB_ANSWER_PROMPT.format(context=context, question=question)
    elif context:
        answer_prompt = ANSWER_PROMPT.format(context=context, question=question)
    else:
        answer_prompt = question

    messages = build_messages(
        question=answer_prompt,
        conversation_history=history,
        user_memory_context=profile_context,
    )

    answer = llm.chat(messages, system=None)

    # Save to conversation history
    conv_memory.add_user_message(question)
    conv_memory.add_assistant_message(answer)

    return {
        "answer": answer,
        "sources": state.get("sources", []),
    }


# ── Node: extract_memory (optional, post-response) ──────────────

def extract_memory(state: AgentState) -> dict:
    """Extract and store memorable facts from the conversation turn."""
    from configs.config import settings
    if not getattr(settings, "MEMORY_EXTRACTION_ENABLED", False):
        return {}

    try:
        llm = _get_llm()
        user_memory = UserMemory(state["user_id"])
        user_memory.extract_and_store(
            user_message=state["question"],
            assistant_response=state.get("answer", ""),
            llm_client=llm,
        )
    except Exception as e:
        logger.debug(f"Memory extraction skipped: {e}")

    return {}
