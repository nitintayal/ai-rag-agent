from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from api.dependencies import get_current_user
from storage.repositories import journal_repo

router = APIRouter(prefix="/journal")


class JournalEntryCreate(BaseModel):
    content: str = Field(..., min_length=1)
    title: Optional[str] = None
    mood: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    entry_date: Optional[str] = None


class JournalEntryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    mood: Optional[str] = None
    tags: Optional[List[str]] = None
    entry_date: Optional[str] = None


class JournalSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    k: int = Field(default=5, ge=1, le=20)


@router.get("/entries")
def list_entries(limit: int = 10, offset: int = 0, user: dict = Depends(get_current_user)):
    return journal_repo.list_entries(user["id"], limit, offset)


@router.post("/entries")
def create_entry(body: JournalEntryCreate, user: dict = Depends(get_current_user)):
    return journal_repo.add_entry(
        user_id=user["id"],
        content=body.content,
        title=body.title,
        mood=body.mood,
        tags=body.tags,
        entry_date=body.entry_date,
    )


@router.get("/entries/{entry_id}")
def get_entry(entry_id: str, user: dict = Depends(get_current_user)):
    entry = journal_repo.get_entry(entry_id, user["id"])
    if not entry:
        raise HTTPException(404, "Entry not found")
    return entry


@router.patch("/entries/{entry_id}")
def update_entry(entry_id: str, body: JournalEntryUpdate, user: dict = Depends(get_current_user)):
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(400, "No fields to update")
    result = journal_repo.update_entry(entry_id, user["id"], **fields)
    if not result:
        raise HTTPException(404, "Entry not found")
    return result


@router.delete("/entries/{entry_id}")
def delete_entry(entry_id: str, user: dict = Depends(get_current_user)):
    if not journal_repo.delete_entry(entry_id, user["id"]):
        raise HTTPException(404, "Entry not found")
    return {"status": "deleted"}


@router.post("/search")
def search_entries(body: JournalSearchRequest, user: dict = Depends(get_current_user)):
    return journal_repo.search_entries(user["id"], body.query, body.k)
