from typing import TypedDict, Optional


class AgentState(TypedDict):
    question: str
    user_id: str
    conversation_id: str
    tool: Optional[str]
    tool_args: Optional[dict]
    tools_plan: Optional[list]  # [{tool, args}, ...] for multi-tool
    context: Optional[str]
    sources: Optional[list[str]]
    messages: Optional[list[dict]]
    answer: Optional[str]
    stream: Optional[bool]
    llm_provider: Optional[str]
    llm_model: Optional[str]
    llm_api_key: Optional[str]
