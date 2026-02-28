from agent.agent_graph import agent


def run_agent(question: str):

    result = agent.invoke({
        "question": question
    })

    return result["answer"]