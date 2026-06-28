"""Entry point for running the agent — sync and streaming variants."""

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


def run_agent(question: str, user_id: str, conversation_id: str) -> dict:
    """Run the agent synchronously. Returns {answer, sources, tool}."""
    state: AgentState = {
        "question": question,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "tool": None,
        "tool_args": None,
        "context": None,
        "sources": None,
        "messages": None,
        "answer": None,
        "stream": False,
    }
    result = agent.invoke(state)
    return {
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "tool": result.get("tool", "direct"),
    }


async def run_agent_stream(question: str, user_id: str, conversation_id: str) -> AsyncIterator[str]:
    """Run routing + tool execution synchronously, then stream the LLM answer."""
    from agent.nodes import route, execute_tool
    from llm.factory import get_llm_client
    from configs.config import settings

    state: AgentState = {
        "question": question,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "tool": None,
        "tool_args": None,
        "context": None,
        "sources": None,
        "messages": None,
        "answer": None,
        "stream": True,
    }

    # Route
    route_result = route(state)
    state["tool"] = route_result["tool"]

    # Execute tool
    tool_result = execute_tool(state)
    state["context"] = tool_result.get("context", "")
    state["sources"] = tool_result.get("sources", [])

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

    # After streaming, save to memory
    answer_text = "".join(full_answer)
    conv_memory.add_user_message(question)
    conv_memory.add_assistant_message(answer_text)

    # Yield sources at the end
    sources = state.get("sources", [])
    if sources:
        yield "\n\nSOURCES:" + json.dumps(sources)

    # Extract memory in background (non-blocking)
    if getattr(settings, "MEMORY_EXTRACTION_ENABLED", False):
        try:
            user_memory.extract_and_store(question, answer_text, llm)
        except Exception as e:
            logger.debug(f"Memory extraction skipped: {e}")
