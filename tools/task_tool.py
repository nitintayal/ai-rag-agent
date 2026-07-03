"""Task tool: manage tasks and reminders."""

from tools.base import BaseTool, ToolDefinition, ToolResult
from storage.repositories import task_repo


class TaskTool(BaseTool):
    definition = ToolDefinition(
        name="task",
        description="Create, list, or manage tasks and reminders",
    )

    def execute(self, user_id: str, action: str = "list", title: str = "",
                description: str | None = None, due_date: str | None = None,
                priority: str = "medium", task_id: str | None = None,
                status: str | None = None, recurrence: str | None = None,
                **kwargs) -> ToolResult:
        try:
            if action == "create" and title:
                task = task_repo.create_task(
                    user_id=user_id, title=title, description=description,
                    due_date=due_date, priority=priority, recurrence=recurrence,
                )
                return ToolResult(
                    context=f"Task created: '{task['title']}' (priority: {task['priority']}, due: {task['due_date'] or 'no deadline'})",
                    data=task,
                )
            elif action == "list":
                tasks = task_repo.list_tasks(user_id, status=status)
                if not tasks:
                    return ToolResult(context="No tasks found.")
                lines = []
                for t in tasks:
                    due = f", due: {t['due_date']}" if t['due_date'] else ""
                    lines.append(f"- [{t['status']}] {t['title']} ({t['priority']}{due})")
                return ToolResult(context=f"Tasks ({len(tasks)}):\n" + "\n".join(lines))
            elif action == "complete" and task_id:
                updated = task_repo.update_task(task_id, user_id, status="done")
                if updated:
                    return ToolResult(context=f"Task '{updated['title']}' marked as done.")
                return ToolResult(context="Task not found.")
            elif action == "delete" and task_id:
                if task_repo.delete_task(task_id, user_id):
                    return ToolResult(context="Task deleted.")
                return ToolResult(context="Task not found.")
            else:
                return ToolResult(context="Use action='create' with title, action='list', action='complete' with task_id, or action='delete' with task_id")
        except Exception as e:
            return ToolResult(error=f"Task operation failed: {e}")
