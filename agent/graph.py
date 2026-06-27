"""LangGraph agent: route → execute_tool → generate → extract_memory."""

from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes import route, execute_tool, generate, extract_memory


def _route_edge(state: AgentState) -> str:
    if state.get("tool") == "direct":
        return "generate"
    return "execute_tool"


def build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("route", route)
    builder.add_node("execute_tool", execute_tool)
    builder.add_node("generate", generate)
    builder.add_node("extract_memory", extract_memory)

    builder.set_entry_point("route")

    builder.add_conditional_edges("route", _route_edge, {
        "execute_tool": "execute_tool",
        "generate": "generate",
    })
    builder.add_edge("execute_tool", "generate")
    builder.add_edge("generate", "extract_memory")
    builder.add_edge("extract_memory", END)

    return builder.compile()


agent = build_graph()
