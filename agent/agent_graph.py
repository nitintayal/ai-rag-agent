from typing import TypedDict
from langgraph.graph import StateGraph, END

from agent.rag_tool import search_documents
from agent.local_llm_answer import answer_with_llm


# ===============================
# Agent State
# ===============================
class AgentState(TypedDict):
    question: str
    context: str
    answer: str
    sources: list[str]


# ===============================
# Retrieval Node
# ===============================
def retrieve(state: AgentState):

    context, sources = search_documents(state["question"])

    return {
        "context": context,
        "sources": sources
    }


# ===============================
# Generation Node
# ===============================
def generate(state: AgentState):
    if not state['context']:
        return {"answer": "I don't have any relevant information to answer that question.", "sources": []}

    prompt = f"""
    Answer using ONLY the provided context.

    Context:
    {state['context']}

    Question:
    {state['question']}
    """

    answer = answer_with_llm(state["question"], state["context"])

    return {
        "answer": answer,
        "sources": state.get("sources", [])
    }


# ===============================
# Build LangGraph Agent ⭐
# ===============================
builder = StateGraph(AgentState)

builder.add_node("retrieve", retrieve)
builder.add_node("generate", generate)

builder.set_entry_point("retrieve")

builder.add_edge("retrieve", "generate")
builder.add_edge("generate", END)

agent = builder.compile()