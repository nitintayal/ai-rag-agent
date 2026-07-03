import logging

from fastapi import APIRouter, HTTPException, Depends

from api.schemas.tasks import TaskCreate, TaskUpdate
from api.dependencies import get_current_user
from storage.repositories import task_repo

router = APIRouter(prefix="/tasks")
logger = logging.getLogger(__name__)


@router.get("")
def list_tasks(status: str | None = None, user: dict = Depends(get_current_user)):
    return task_repo.list_tasks(user["id"], status=status)


@router.post("")
def create_task(body: TaskCreate, user: dict = Depends(get_current_user)):
    return task_repo.create_task(
        user_id=user["id"], title=body.title, description=body.description,
        due_date=body.due_date, priority=body.priority, recurrence=body.recurrence,
    )


@router.get("/send-reminders")
def send_reminders(user: dict = Depends(get_current_user)):
    """Send due-date reminder emails for this user's overdue/due-today tasks."""
    from auth.email import send_task_reminder_email
    tasks = task_repo.get_tasks_due_today(user_id=user["id"])
    sent = 0
    for task in tasks:
        try:
            email = user.get("email") or task.get("email")
            name = user.get("name") or task.get("name") or "there"
            if email and send_task_reminder_email(email, name, [task]):
                task_repo.mark_reminder_sent(task["id"])
                sent += 1
        except Exception as e:
            logger.error(f"Reminder failed for task {task['id']}: {e}")
    return {"sent": sent, "total": len(tasks)}


@router.get("/{task_id}")
def get_task(task_id: str, user: dict = Depends(get_current_user)):
    task = task_repo.get_task(task_id, user["id"])
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.patch("/{task_id}")
def update_task(task_id: str, body: TaskUpdate, user: dict = Depends(get_current_user)):
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(400, "No fields to update")
    result = task_repo.update_task(task_id, user["id"], **fields)
    if not result:
        raise HTTPException(404, "Task not found")
    return result


@router.delete("/{task_id}")
def delete_task(task_id: str, user: dict = Depends(get_current_user)):
    if not task_repo.delete_task(task_id, user["id"]):
        raise HTTPException(404, "Task not found")
    return {"status": "deleted"}
