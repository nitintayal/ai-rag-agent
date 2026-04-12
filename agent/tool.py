from agent.web_tool import web_search_tool
from agent.rag_tool import rag_search_tool

TOOLS = {
    "rag": rag_search_tool,
    "web": web_search_tool
}

def decide_tool(state):
    query = state["query"].lower()

    if any(x in query for x in ["latest", "today", "news", "current"]):
        return "web"

    return "rag"

