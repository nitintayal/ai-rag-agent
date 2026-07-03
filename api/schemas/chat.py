from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    user_id: str = Field(default="default-user")
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []
    tool: str = "direct"
    conversation_id: Optional[str] = None
