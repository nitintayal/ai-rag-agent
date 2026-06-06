import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

mcp = FastMCP("rag")


@mcp.tool()
def search_documents(query: str):
    """Search the local knowledge base with the project's hybrid RAG pipeline."""
    from agent.rag_tool import hybrid_search_documents

    context, sources, should_fallback = hybrid_search_documents(query)
    return {
        "context": context,
        "sources": sources,
        "should_fallback": should_fallback,
    }


if __name__ == "__main__":
    mcp.run()
