"""Builds the full message list for the LLM from conversation history, user memory, and tool results."""

from llm.prompts import SYSTEM_PROMPT


def build_messages(
    question: str,
    conversation_history: list[dict] | None = None,
    user_memory_context: str = "",
    tool_context: str = "",
    system_prompt: str | None = None,
) -> list[dict]:
    """Build the Ollama-compatible message list.

    Order: system (with user memory) → conversation history → tool context (if any) → current question.
    """
    messages = []

    # System prompt with user memory injected
    sys = system_prompt or SYSTEM_PROMPT
    if user_memory_context:
        sys = f"{sys}\n\n{user_memory_context}"
    messages.append({"role": "system", "content": sys})

    # Conversation history (already in [{role, content}, ...] format)
    if conversation_history:
        messages.extend(conversation_history)

    # Current user message — with tool context if available
    if tool_context:
        user_content = f"Context from tools:\n{tool_context}\n\nUser question: {question}"
    else:
        user_content = question

    messages.append({"role": "user", "content": user_content})

    return messages
