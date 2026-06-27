from typing import TypedDict, Optional


class AgentState(TypedDict):
    question: str
    user_id: str
    conversation_id: str
    tool: Optional[str]
    tool_args: Optional[dict]
    context: Optional[str]
    sources: Optional[list[str]]
    messages: Optional[list[dict]]
    answer: Optional[str]
    stream: Optional[bool]
