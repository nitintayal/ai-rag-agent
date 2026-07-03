from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from api.dependencies import get_current_user
from storage.repositories import calendar_repo

router = APIRouter(prefix="/calendar")


class EventCreate(BaseModel):
    title: str
    start_time: str
    end_time: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    all_day: bool = False
    recurrence: Optional[str] = None  # "daily" | "weekly" | "monthly"


class EventUpdate(BaseModel):
    title: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    all_day: Optional[bool] = None
    recurrence: Optional[str] = None


@router.get("/events")
def list_events(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    user: dict = Depends(get_current_user),
):
    return calendar_repo.list_events(user["id"], limit=limit, start=start, end=end)


@router.post("/events")
def create_event(body: EventCreate, user: dict = Depends(get_current_user)):
    return calendar_repo.create_event(
        user_id=user["id"], title=body.title, start_time=body.start_time,
        end_time=body.end_time, description=body.description,
        location=body.location, all_day=body.all_day, recurrence=body.recurrence,
    )


@router.get("/events/{event_id}")
def get_event(event_id: str, user: dict = Depends(get_current_user)):
    event = calendar_repo.get_event(event_id, user["id"])
    if not event:
        raise HTTPException(404, "Event not found")
    return event


@router.patch("/events/{event_id}")
def update_event(event_id: str, body: EventUpdate, user: dict = Depends(get_current_user)):
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(400, "No fields to update")
    result = calendar_repo.update_event(event_id, user["id"], **fields)
    if not result:
        raise HTTPException(404, "Event not found")
    return result


@router.delete("/events/{event_id}")
def delete_event(event_id: str, user: dict = Depends(get_current_user)):
    if not calendar_repo.delete_event(event_id, user["id"]):
        raise HTTPException(404, "Event not found")
    return {"status": "deleted"}
