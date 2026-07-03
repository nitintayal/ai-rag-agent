"""Graph node functions for the agent."""

import json
import logging

from agent.state import AgentState
from llm.factory import get_llm_client
from llm.prompts import ROUTER_PROMPT, ANSWER_PROMPT, WEB_ANSWER_PROMPT
from memory.context_builder import build_messages
from memory.conversation_memory import ConversationMemory
from memory.long_term_memory import UserMemory
from tools.registry import get_tool

logger = logging.getLogger(__name__)

_KEYWORD_WEB_TRIGGERS = {"latest", "current", "today", "news", "weather", "stock", "price", "now", "recent"}
_VALID_TOOLS = {"rag", "web", "journal", "task", "memory", "calendar", "direct"}


def _get_llm(state: AgentState | None = None):
    if state and (state.get("llm_provider") or state.get("llm_model") or state.get("llm_api_key")):
        return get_llm_client(
            provider=state.get("llm_provider"),
            model=state.get("llm_model"),
            api_key=state.get("llm_api_key"),
        )
    return get_llm_client()


def _keyword_fallback_route(question: str) -> list[dict]:
    q = question.lower()
    if any(w in q for w in _KEYWORD_WEB_TRIGGERS):
        return [{"tool": "web", "args": {"query": question}}]
    if any(w in q for w in ("journal", "diary", "note", "reflect")):
        return [{"tool": "journal", "args": {"action": "search", "query": question}}]
    if any(w in q for w in ("task", "todo", "remind", "deadline")):
        return [{"tool": "task", "args": {"action": "list"}}]
    if any(w in q for w in ("remember", "preference", "my name", "i am", "i like", "i prefer")):
        return [{"tool": "memory", "args": {"action": "store"}}]
    if any(w in q for w in ("calendar", "event", "meeting", "schedule", "appointment")):
        return [{"tool": "calendar", "args": {"action": "list"}}]
    return [{"tool": "direct", "args": {}}]


# ── Node: route ──────────────────────────────────────────────────

def route(state: AgentState) -> dict:
    """Single LLM call: decide which tool(s) AND extract arguments."""
    question = state["question"]
    llm = _get_llm(state)

    try:
        prompt = ROUTER_PROMPT.format(question=question)
        result = llm.chat(
            [{"role": "user", "content": prompt}],
            system="You are a router that picks the right tool(s) and extracts parameters. Respond only with valid JSON.",
            format="json",
        )
        parsed = json.loads(result)

        # Handle new multi-tool format: {"tools": [...]}
        tools_list = parsed.get("tools", [])
        if not tools_list:
            # Fallback to old single-tool format: {"tool": "...", "args": {...}}
            tool = parsed.get("tool", "direct")
            args = parsed.get("args", {})
            if tool in _VALID_TOOLS:
                tools_list = [{"tool": tool, "args": args}]

        # Validate
        valid = [t for t in tools_list if t.get("tool") in _VALID_TOOLS]
        if valid:
            logger.info(f"LLM routed to: {[t['tool'] for t in valid]}")
            first = valid[0]
            return {
                "tool": first["tool"],
                "tool_args": first.get("args", {}),
                "tools_plan": valid if len(valid) > 1 else None,
            }
    except Exception as e:
        logger.debug(f"LLM routing failed, using keyword fallback: {e}")

    fallback = _keyword_fallback_route(question)
    logger.info(f"Keyword routed to: {fallback[0]['tool']}")
    return {
        "tool": fallback[0]["tool"],
        "tool_args": fallback[0].get("args", {}),
        "tools_plan": None,
    }


# ── Node: execute_tool ───────────────────────────────────────────

def execute_tool(state: AgentState) -> dict:
    """Execute one or more tools and combine context."""
    tools_plan = state.get("tools_plan")

    def _run_tool(tool_name, args):
        tool = get_tool(tool_name)
        if not tool:
            return None
        merged = {"query": state["question"], **args}
        return tool.execute(user_id=state["user_id"], **merged)

    # Multi-tool: execute all and merge context
    if tools_plan and len(tools_plan) > 1:
        all_context = []
        all_sources = []
        for plan in tools_plan:
            if plan["tool"] == "direct":
                continue
            result = _run_tool(plan["tool"], plan.get("args", {}))
            if not result:
                continue
            if result.ok and result.context:
                all_context.append(f"[{plan['tool'].upper()} results]\n{result.context}")
                all_sources.extend(result.sources or [])
            elif result.error:
                logger.error(f"Tool {plan['tool']} error: {result.error}")
                all_context.append(f"[{plan['tool'].upper()} error]\n{result.error}")

        return {"context": "\n\n".join(all_context), "sources": all_sources}

    # Single tool
    tool_name = state.get("tool", "direct")
    if tool_name == "direct":
        return {"context": "", "sources": []}

    result = _run_tool(tool_name, state.get("tool_args") or {})
    if not result:
        return {"context": "", "sources": []}

    if result.error:
        logger.error(f"Tool {tool_name} error: {result.error}")
        return {"context": f"Tool error: {result.error}", "sources": []}

    return {"context": result.context, "sources": result.sources or []}


# ── Node: generate ───────────────────────────────────────────────

def generate(state: AgentState) -> dict:
    question = state["question"]
    context = state.get("context", "")
    tool = state.get("tool", "direct")
    user_id = state["user_id"]
    conversation_id = state["conversation_id"]

    llm = _get_llm(state)

    conv_memory = ConversationMemory(conversation_id, user_id)
    user_memory = UserMemory(user_id)

    history = conv_memory.get_history()
    profile_context = user_memory.get_profile_context()

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

    conv_memory.add_user_message(question)
    conv_memory.add_assistant_message(answer)

    return {
        "answer": answer,
        "sources": state.get("sources", []),
    }


# ── Node: extract_memory ────────────────────────────────────────

def extract_memory(state: AgentState) -> dict:
    from configs.config import settings
    if not getattr(settings, "MEMORY_EXTRACTION_ENABLED", False):
        return {}

    try:
        llm = _get_llm(state)
        user_memory = UserMemory(state["user_id"])
        user_memory.extract_and_store(
            user_message=state["question"],
            assistant_response=state.get("answer", ""),
            llm_client=llm,
        )
    except Exception as e:
        logger.debug(f"Memory extraction skipped: {e}")

    return {}
