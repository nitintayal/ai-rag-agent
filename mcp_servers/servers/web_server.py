import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.web_tool import web_search_tool

mcp = FastMCP("web")


@mcp.tool()
def search_web(query: str):
    """Search the public web and return fetched context plus source URLs."""
    return web_search_tool(query)


if __name__ == "__main__":
    mcp.run()
