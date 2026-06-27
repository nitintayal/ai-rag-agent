from langgraph.graph import StateGraph, END

from agent.local_llm_answer import answer_with_llm, decide_llm_tool
from agent.agent_state import AgentState
from mcp_servers.client.mcp_client import search_documents, search_web



# ===============================
# MCP Tool Node
# ===============================
def mcp_executor(state: AgentState):
    tool = state.get("tool", "rag")
    question = state["question"]

    if tool == "web":
        print("\n🧠 MCP server selected: Web")
        result = search_web(question)
        return {
            "tool": "web",
            "context": result.get("context", ""),
            "sources": result.get("sources", []),
        }

    print("\n🧠 MCP server selected: RAG")
    result = search_documents(question)
    context = result.get("context", "")
    sources = result.get("sources", [])

    return {"tool": "rag", "context": context, "sources": sources}


# ===============================
# Generation Node
# ===============================
def generate(state: AgentState):
    if not state['context']:
        return {"answer": "I don't have any relevant information to answer that question.", "sources": []}

    answer = answer_with_llm(
        state["question"],
        state["context"],
        state.get("tool", "rag"),
    )

    return {
        "answer": answer,
        "sources": state.get("sources", [])
    }


# ===============================
# Build LangGraph Agent ⭐
# ===============================
builder = StateGraph(AgentState)

builder.add_node("decide", decide_llm_tool)
builder.add_node("tool_executor", mcp_executor)
builder.add_node("generate", generate)

builder.add_conditional_edges(
    "decide",
    lambda state: state["tool"],
    {
        "rag": "tool_executor",
        "web": "tool_executor",
    }
)
builder.add_edge("tool_executor", "generate")

builder.set_entry_point("decide")
builder.set_finish_point("generate")

builder.add_edge("generate", END)

agent = builder.compile()
