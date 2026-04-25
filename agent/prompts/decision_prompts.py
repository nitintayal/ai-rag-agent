def decide_tool(state):

    prompt = f"""
    Decide which tool to use:

    Tools:
    - rag: for internal documents
    - web: for latest or external info

    Query: {state['query']}

    Answer ONLY: rag or web
    """

    tool = llm(prompt).strip().lower()
    return tool