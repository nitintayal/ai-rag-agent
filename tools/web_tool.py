"""Web search tool: searches the web via DuckDuckGo."""

from tools.base import BaseTool, ToolDefinition, ToolResult
from agent.web_tool import web_search_tool


class WebTool(BaseTool):
    definition = ToolDefinition(
        name="web",
        description="Search the web for current/recent information",
    )

    def execute(self, user_id: str, query: str = "", **kwargs) -> ToolResult:
        try:
            result = web_search_tool(query)
            context = result.get("context", "")
            sources = result.get("sources", [])
            if not context:
                return ToolResult(context="No web results found.", sources=[])
            return ToolResult(context=context, sources=sources)
        except Exception as e:
            return ToolResult(error=f"Web search failed: {e}")
