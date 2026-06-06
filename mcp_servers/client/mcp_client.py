import asyncio
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "mcp_servers" / "servers.json"


class MCPClientError(RuntimeError):
    pass


def _load_server_config(server_name: str, config_path: Path = DEFAULT_CONFIG_PATH):
    with config_path.open("r", encoding="utf-8") as config_file:
        servers = json.load(config_file)["mcpServers"]
    try:
        return servers[server_name]
    except KeyError as exc:
        raise MCPClientError(f"Unknown MCP server: {server_name}") from exc


def _decode_tool_result(result: Any):
    if getattr(result, "structured_content", None) is not None:
        return result.structured_content
    if getattr(result, "structuredContent", None) is not None:
        return result.structuredContent

    content = getattr(result, "content", None)
    if not content:
        return {}

    first_item = content[0]
    text = getattr(first_item, "text", None)
    if text is None:
        return first_item

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


async def _call_tool_async(server_name: str, tool_name: str, arguments: dict[str, Any]):
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ModuleNotFoundError as exc:
        raise MCPClientError(
            "MCP SDK is not installed. Run `pip install -r requirements.txt`."
        ) from exc

    server_config = _load_server_config(server_name)
    server_params = StdioServerParameters(
        command=server_config["command"],
        args=server_config.get("args", []),
        cwd=str(PROJECT_ROOT),
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            return _decode_tool_result(result)


def call_mcp_tool(server_name: str, tool_name: str, arguments: dict[str, Any]):
    return asyncio.run(_call_tool_async(server_name, tool_name, arguments))


def search_documents(query: str):
    return call_mcp_tool("rag", "search_documents", {"query": query})


def search_web(query: str):
    return call_mcp_tool("web", "search_web", {"query": query})


def search_journal_entries(user_id: str, query: str, k: int = 5):
    return call_mcp_tool(
        "journal",
        "search_journal_entries",
        {"user_id": user_id, "query": query, "k": k},
    )
