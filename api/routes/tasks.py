from fastapi import APIRouter, HTTPException

from api.schemas.tasks import TaskCreate, TaskUpdate
from storage.repositories import task_repo

router = APIRouter(prefix="/tasks")


@router.get("")
def list_tasks(user_id: str = "default-user", status: str | None = None):
    return task_repo.list_tasks(user_id, status=status)


@router.post("")
def create_task(body: TaskCreate, user_id: str = "default-user"):
    return task_repo.create_task(
        user_id=user_id, title=body.title, description=body.description,
        due_date=body.due_date, priority=body.priority,
    )


@router.get("/{task_id}")
def get_task(task_id: str, user_id: str = "default-user"):
    task = task_repo.get_task(task_id, user_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.patch("/{task_id}")
def update_task(task_id: str, body: TaskUpdate, user_id: str = "default-user"):
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(400, "No fields to update")
    result = task_repo.update_task(task_id, user_id, **fields)
    if not result:
        raise HTTPException(404, "Task not found")
    return result


@router.delete("/{task_id}")
def delete_task(task_id: str, user_id: str = "default-user"):
    if not task_repo.delete_task(task_id, user_id):
        raise HTTPException(404, "Task not found")
    return {"status": "deleted"}
