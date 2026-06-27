from fastapi import APIRouter, HTTPException

from storage.repositories import journal_repo

router = APIRouter(prefix="/journal")


@router.get("/entries")
def list_entries(user_id: str = "default-user", limit: int = 10, offset: int = 0):
    return journal_repo.list_entries(user_id, limit, offset)


@router.post("/entries")
def create_entry(
    user_id: str = "default-user",
    content: str = "",
    title: str | None = None,
    mood: str | None = None,
):
    if not content:
        raise HTTPException(400, "Content is required")
    return journal_repo.add_entry(user_id=user_id, content=content, title=title, mood=mood)


@router.get("/entries/{entry_id}")
def get_entry(entry_id: str, user_id: str = "default-user"):
    entry = journal_repo.get_entry(entry_id, user_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    return entry


@router.patch("/entries/{entry_id}")
def update_entry(entry_id: str, user_id: str = "default-user",
                 title: str | None = None, content: str | None = None,
                 mood: str | None = None):
    fields = {k: v for k, v in {"title": title, "content": content, "mood": mood}.items() if v is not None}
    if not fields:
        raise HTTPException(400, "No fields to update")
    result = journal_repo.update_entry(entry_id, user_id, **fields)
    if not result:
        raise HTTPException(404, "Entry not found")
    return result


@router.delete("/entries/{entry_id}")
def delete_entry(entry_id: str, user_id: str = "default-user"):
    if not journal_repo.delete_entry(entry_id, user_id):
        raise HTTPException(404, "Entry not found")
    return {"status": "deleted"}


@router.post("/search")
def search_entries(user_id: str = "default-user", query: str = "", k: int = 5):
    if not query:
        raise HTTPException(400, "Query is required")
    return journal_repo.search_entries(user_id, query, k)
