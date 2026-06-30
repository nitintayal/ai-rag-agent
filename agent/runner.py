"""Entry point for running the agent — sync and streaming variants."""

import asyncio
import json
import logging
from typing import AsyncIterator

from agent.graph import agent
from agent.state import AgentState
from llm.factory import get_llm_client
from llm.prompts import ANSWER_PROMPT, WEB_ANSWER_PROMPT
from memory.context_builder import build_messages
from memory.conversation_memory import ConversationMemory
from memory.long_term_memory import UserMemory

logger = logging.getLogger(__name__)


def _empty_state(question, user_id, conversation_id, stream=False) -> AgentState:
    return {
        "question": question,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "tool": None,
        "tool_args": None,
        "tools_plan": None,
        "context": None,
        "sources": None,
        "messages": None,
        "answer": None,
        "stream": stream,
    }


def run_agent(question: str, user_id: str, conversation_id: str) -> dict:
    state = _empty_state(question, user_id, conversation_id)
    result = agent.invoke(state)
    return {
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "tool": result.get("tool", "direct"),
    }


async def run_agent_stream(question: str, user_id: str, conversation_id: str) -> AsyncIterator[str]:
    from agent.nodes import route, execute_tool
    from configs.config import settings

    state = _empty_state(question, user_id, conversation_id, stream=True)

    # Send an immediate heartbeat so the HTTP connection opens right away —
    # otherwise route()/execute_tool() can block for 10-30s (e.g. slow web
    # search) with zero bytes sent, causing proxies/browsers to drop the
    # connection before any response arrives.
    yield ""

    # Route + extract args (supports multi-tool) — run off the event loop, bounded
    try:
        route_result = await asyncio.wait_for(asyncio.to_thread(route, state), timeout=15)
        state["tool"] = route_result["tool"]
        state["tool_args"] = route_result.get("tool_args", {})
        state["tools_plan"] = route_result.get("tools_plan")
    except asyncio.TimeoutError:
        logger.warning("Routing timed out, answering directly")
        state["tool"] = "direct"
        state["tool_args"] = {}
        state["tools_plan"] = None

    # Execute tool(s) — also off the event loop, bounded so a slow tool
    # (e.g. web search) can never hang the whole request indefinitely
    try:
        tool_result = await asyncio.wait_for(asyncio.to_thread(execute_tool, state), timeout=20)
        state["context"] = tool_result.get("context", "")
        state["sources"] = tool_result.get("sources", [])
    except asyncio.TimeoutError:
        logger.warning(f"Tool '{state.get('tool')}' execution timed out")
        state["context"] = ""
        state["sources"] = []

    # Build messages for streaming
    conv_memory = ConversationMemory(conversation_id, user_id)
    user_memory = UserMemory(user_id)

    history = conv_memory.get_history()
    profile_context = user_memory.get_profile_context()

    context = state.get("context", "")
    tool = state.get("tool", "direct")

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

    # Stream tokens
    llm = get_llm_client()
    full_answer = []

    async for token in llm.chat_stream(messages, system=None):
        full_answer.append(token)
        yield token

    answer_text = "".join(full_answer)
    conv_memory.add_user_message(question)
    conv_memory.add_assistant_message(answer_text)

    sources = state.get("sources", [])
    if sources:
        yield "\n\nSOURCES:" + json.dumps(sources)

    if getattr(settings, "MEMORY_EXTRACTION_ENABLED", False):
        try:
            user_memory.extract_and_store(question, answer_text, llm)
        except Exception as e:
            logger.debug(f"Memory extraction skipped: {e}")
