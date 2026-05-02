from langgraph.graph import StateGraph, END

from agent.rag_tool import run_rag
from agent.local_llm_answer import answer_with_llm, decide_llm_tool
from agent.web_tool import web_search_tool
from agent.agent_state import AgentState



# ===============================
# Retrieval Node
# ===============================
def rag_search_tool(state: AgentState):
    print("\n🧠 Tool selected: RAG Search")
    context, sources, should_fallback = run_rag(state["question"])

    if should_fallback or not context:
        print("\n↪️ RAG confidence too low, falling back to Web Search")
        result = web_search_tool(state["question"])
        return {
            "tool": "web",
            "context": result.get("context", ""),
            "sources": result.get("sources", [])
        }

    return {
        "tool": "rag",
        "context": context,
        "sources": sources
    }


def web_search_node(state: AgentState):
    print("\n🧠 Tool selected: Web Search")
    result = web_search_tool(state["question"])

    return {
        "context": result.get("context", ""),
        "sources": result.get("sources", [])
    }


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
builder.add_node("rag", rag_search_tool)
builder.add_node("web", web_search_node)
builder.add_node("generate", generate)

builder.add_conditional_edges(
    "decide",
    lambda state: state["tool"],
    {
        "rag": "rag",
        "web": "web"
    }
)
builder.add_edge("rag", "generate")
builder.add_edge("web", "generate")

builder.set_entry_point("decide")
builder.set_finish_point("generate")

builder.add_edge("generate", END)

agent = builder.compile()
