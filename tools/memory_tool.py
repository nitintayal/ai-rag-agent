"""Memory tool: store and recall user facts and preferences."""

from tools.base import BaseTool, ToolDefinition, ToolResult
from memory.long_term_memory import UserMemory


class MemoryTool(BaseTool):
    definition = ToolDefinition(
        name="memory",
        description="Store or recall facts about the user",
    )

    def execute(self, user_id: str, action: str = "recall", key: str = "",
                value: str = "", category: str = "general",
                query: str = "", **kwargs) -> ToolResult:
        try:
            user_memory = UserMemory(user_id)

            if action == "store" and key and value:
                user_memory.store(key, value, category)
                return ToolResult(context=f"Remembered: {key} = {value}")
            elif action == "recall" and query:
                results = user_memory.recall_by_query(query, k=5)
                if not results:
                    return ToolResult(context="No relevant memories found.")
                lines = [f"- {r['memory']['key']}: {r['memory']['value']}" for r in results]
                return ToolResult(context="Recalled memories:\n" + "\n".join(lines))
            elif action == "list":
                memories = user_memory.get_all(category=category if category != "general" else None)
                if not memories:
                    return ToolResult(context="No stored memories.")
                lines = [f"- {m['key']}: {m['value']}" for m in memories]
                return ToolResult(context="All memories:\n" + "\n".join(lines))
            elif action == "forget" and key:
                if user_memory.forget(key):
                    return ToolResult(context=f"Forgot: {key}")
                return ToolResult(context=f"No memory found for key: {key}")
            else:
                return ToolResult(context="Use action='store' with key+value, action='recall' with query, action='list', or action='forget' with key")
        except Exception as e:
            return ToolResult(error=f"Memory operation failed: {e}")
