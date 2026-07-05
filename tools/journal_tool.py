"""Journal tool: CRUD + search on journal entries via the storage layer."""

import json

from tools.base import BaseTool, ToolDefinition, ToolResult
from storage.repositories import journal_repo


class JournalTool(BaseTool):
    definition = ToolDefinition(
        name="journal",
        description="Create, search, or manage journal entries",
    )

    def execute(self, user_id: str, action: str = "search", query: str = "",
                title: str | None = None, content: str | None = None,
                mood: str | None = None, **kwargs) -> ToolResult:
        try:
            if action == "create" and content:
                entry = journal_repo.add_entry(
                    user_id=user_id, content=content, title=title, mood=mood,
                )
                return ToolResult(
                    context=f"Journal entry created: {entry['title'] or 'Untitled'}",
                    data=entry,
                )
            elif action == "search":
                if query:
                    results = journal_repo.search_entries(user_id, query, k=5)
                    if not results:
                        return ToolResult(context="No matching journal entries found.")
                    entries_text = "\n\n".join(
                        f"[{r['entry'].get('entry_date', '')}] {r['entry'].get('title', 'Untitled')}\n{r['entry']['content']}"
                        for r in results
                    )
                    return ToolResult(context=entries_text)
                else:
                    # No query — fall through to list with content
                    action = "list"
            if action == "list":
                page = journal_repo.list_entries(user_id, limit=5)
                entries = page["items"]
                if not entries:
                    return ToolResult(context="No journal entries found.")
                entries_text = "\n\n".join(
                    f"[{e.get('entry_date', '')}] {e.get('title', 'Untitled')}\n{e.get('content', '').strip() or '(no content)'}"
                    for e in entries
                )
                return ToolResult(context=f"Recent journal entries:\n\n{entries_text}")
            else:
                return ToolResult(context="Use action='search' with a query, action='create' with content, or action='list'")
        except Exception as e:
            return ToolResult(error=f"Journal operation failed: {e}")
