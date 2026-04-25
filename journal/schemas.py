from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class JournalEntryCreate(BaseModel):
    user_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    title: Optional[str] = None
    mood: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    entry_date: Optional[date] = None


class JournalEntryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = Field(default=None, min_length=1)
    mood: Optional[str] = None
    tags: Optional[List[str]] = None
    entry_date: Optional[date] = None


class JournalEntryResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str]
    content: str
    mood: Optional[str]
    tags: List[str]
    entry_date: str
    created_at: datetime
    updated_at: Optional[datetime]


class JournalEntriesPage(BaseModel):
    items: List[JournalEntryResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class JournalSearchRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    k: int = Field(default=5, ge=1, le=20)


class JournalSearchResult(BaseModel):
    entry: JournalEntryResponse
    score: float
