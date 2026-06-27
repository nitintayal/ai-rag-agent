"""RAG tool: searches the user's uploaded documents via hybrid search + reranking."""

from tools.base import BaseTool, ToolDefinition, ToolResult
from agent.rag_tool import hybrid_search_documents


class RagTool(BaseTool):
    definition = ToolDefinition(
        name="rag",
        description="Search the user's uploaded documents and knowledge base",
    )

    def execute(self, user_id: str, query: str = "", **kwargs) -> ToolResult:
        try:
            context, sources, should_fallback = hybrid_search_documents(query)
            if should_fallback or not context:
                return ToolResult(
                    context="No relevant documents found in the knowledge base.",
                    sources=[],
                )
            return ToolResult(context=context, sources=sources)
        except Exception as e:
            return ToolResult(error=f"RAG search failed: {e}")
