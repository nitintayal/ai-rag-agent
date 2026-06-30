"""Web search tool: dispatches to the configured search provider (ddgs or tavily)."""

import logging

from tools.base import BaseTool, ToolDefinition, ToolResult
from configs.config import settings

logger = logging.getLogger(__name__)


def web_search(query: str) -> dict:
    provider = settings.WEB_SEARCH_PROVIDER.lower()

    if provider == "tavily" and settings.TAVILY_API_KEY:
        logger.info("Using web search provider: tavily")
        from tools.web_search import tavily_search
        return tavily_search.search(query)

    if provider == "tavily" and not settings.TAVILY_API_KEY:
        logger.warning("WEB_SEARCH_PROVIDER=tavily but TAVILY_API_KEY missing — falling back to ddgs")

    logger.info("Using web search provider: ddgs")
    from tools.web_search import ddgs_search
    return ddgs_search.search(query)


class WebTool(BaseTool):
    definition = ToolDefinition(
        name="web",
        description="Search the web for current/recent information",
    )

    def execute(self, user_id: str, query: str = "", **kwargs) -> ToolResult:
        try:
            result = web_search(query)
            context = result.get("context", "")
            sources = result.get("sources", [])
            if not context:
                return ToolResult(context="No web results found.", sources=[])
            return ToolResult(context=context, sources=sources)
        except Exception as e:
            return ToolResult(error=f"Web search failed: {e}")
