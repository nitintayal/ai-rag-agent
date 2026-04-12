
# ===============================
# Agent State
# ===============================
from typing import TypedDict, Optional, List


class AgentState(TypedDict):
    question: str
    tool: Optional[str]
    context: Optional[str]
    answer: Optional[str]
    sources: Optional[List[str]]

    def __init__(self, question: str):
        self.question = question
        self.context = ""
        self.answer = ""
        self.sources = []

