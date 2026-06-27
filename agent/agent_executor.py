from configs.config import settings
from .model import get_agent_mode


def run_agent(question: str, user_id: str = "demo-user"):
    if get_agent_mode() == "deep":
        from agent.deep_agent import run_deep_agent

        return run_deep_agent(question=question, user_id=user_id)

    from agent.agent_graph import agent
    from agent.agent_state import AgentState

    state = AgentState(question=question)
    result = agent.invoke(state)
    return result
