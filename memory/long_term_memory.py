"""Long-term memory: user facts and preferences that persist across conversations."""

import json
import logging

from storage.repositories import memory_repo

logger = logging.getLogger(__name__)


class UserMemory:
    def __init__(self, user_id: str):
        self.user_id = user_id

    def store(self, key: str, value: str, category: str = "general") -> dict:
        embedding = self._safe_embed(f"{key}: {value}")
        return memory_repo.store_memory(
            self.user_id, key, value, category, embedding=embedding,
        )

    def recall_by_key(self, key: str) -> str | None:
        mem = memory_repo.get_memory(self.user_id, key)
        return mem["value"] if mem else None

    def recall_by_query(self, query: str, k: int = 5) -> list[dict]:
        embedding = self._safe_embed(query)
        if not embedding:
            return []
        return memory_repo.search_memories(self.user_id, embedding, k=k)

    @staticmethod
    def _safe_embed(text: str) -> list[float] | None:
        try:
            from rag.embeddings import embed_query
            return embed_query(text).tolist()
        except ImportError:
            return None

    def get_all(self, category: str | None = None) -> list[dict]:
        return memory_repo.list_memories(self.user_id, category=category)

    def forget(self, key: str) -> bool:
        return memory_repo.delete_memory(self.user_id, key)

    def get_profile_context(self) -> str:
        """Returns a formatted string of all known user facts for system prompt injection."""
        memories = self.get_all()
        if not memories:
            return ""
        lines = ["Known facts about this user:"]
        for m in memories:
            lines.append(f"- {m['key']}: {m['value']}")
        return "\n".join(lines)

    def extract_and_store(self, user_message: str, assistant_response: str, llm_client) -> None:
        """Extract memorable facts from a conversation turn using the LLM."""
        from llm.prompts import MEMORY_EXTRACTION_PROMPT

        prompt = MEMORY_EXTRACTION_PROMPT.format(
            user_message=user_message,
            assistant_response=assistant_response,
        )
        try:
            result = llm_client.chat(
                [{"role": "user", "content": prompt}],
                system="You extract personal facts from conversations. Respond only with JSON or NONE.",
            )
            result = result.strip()
            if result.upper() == "NONE" or not result.startswith("["):
                return

            facts = json.loads(result)
            for fact in facts:
                if "key" in fact and "value" in fact:
                    self.store(
                        fact["key"], fact["value"],
                        category=fact.get("category", "general"),
                    )
                    logger.info(f"Stored memory: {fact['key']} = {fact['value']}")
        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"Memory extraction skipped: {e}")
