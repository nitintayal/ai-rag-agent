"""Short-term memory: conversation message history from the database."""

from storage.repositories import conversation_repo, user_repo


class ConversationMemory:
    def __init__(self, conversation_id: str, user_id: str, history_limit: int = 20):
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.history_limit = history_limit
        user_repo.ensure_user(user_id)
        conversation_repo.create_conversation(user_id, conversation_id=conversation_id)

    def add_user_message(self, content: str) -> None:
        conversation_repo.add_message(self.conversation_id, "user", content)

    def add_assistant_message(self, content: str) -> None:
        conversation_repo.add_message(self.conversation_id, "assistant", content)

    def add_tool_message(self, content: str, tool_name: str) -> None:
        conversation_repo.add_message(
            self.conversation_id, "tool", content, tool_name=tool_name,
        )

    def get_history(self) -> list[dict]:
        """Returns recent messages as [{role, content}, ...] for the LLM."""
        messages = conversation_repo.get_messages(self.conversation_id, limit=self.history_limit)
        return [{"role": m["role"], "content": m["content"]} for m in messages]

    def get_history_text(self) -> str:
        """Returns conversation history as a formatted string for context injection."""
        messages = self.get_history()
        if not messages:
            return ""
        lines = []
        for m in messages:
            role = "User" if m["role"] == "user" else "Assistant"
            lines.append(f"{role}: {m['content']}")
        return "\n".join(lines)
