"""Tool registry — single place to look up all available tools."""

from tools.base import BaseTool
from tools.rag_tool import RagTool
from tools.web_tool import WebTool
from tools.journal_tool import JournalTool
from tools.task_tool import TaskTool
from tools.memory_tool import MemoryTool
from tools.calendar_tool import CalendarTool

_TOOLS: dict[str, BaseTool] = {}


def _register_defaults():
    global _TOOLS
    if _TOOLS:
        return
    for cls in [RagTool, WebTool, JournalTool, TaskTool, MemoryTool, CalendarTool]:
        tool = cls()
        _TOOLS[tool.definition.name] = tool


def get_all_tools() -> list[BaseTool]:
    _register_defaults()
    return list(_TOOLS.values())


def get_tool(name: str) -> BaseTool | None:
    _register_defaults()
    return _TOOLS.get(name)


def get_tool_descriptions() -> str:
    """Formatted tool list for LLM prompts."""
    _register_defaults()
    lines = []
    for tool in _TOOLS.values():
        lines.append(f"- {tool.definition.name}: {tool.definition.description}")
    return "\n".join(lines)
