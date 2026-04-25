from agent.agent_graph import agent
from agent.agent_state import AgentState


def run_agent(question: str):
    state = AgentState(question=question)
    result = agent.invoke(state)
    return result