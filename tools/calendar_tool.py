"""Calendar tool: simple event management via the storage abstraction."""

from tools.base import BaseTool, ToolDefinition, ToolResult
from storage.repositories import calendar_repo


class CalendarTool(BaseTool):
    definition = ToolDefinition(
        name="calendar",
        description="Create or check calendar events",
    )

    def execute(self, user_id: str, action: str = "list", title: str = "",
                start_time: str = "", end_time: str | None = None,
                description: str | None = None, event_id: str | None = None,
                **kwargs) -> ToolResult:
        try:
            if action == "create" and title and start_time:
                event = calendar_repo.create_event(user_id, title, start_time, end_time, description)
                return ToolResult(
                    context=f"Event created: '{title}' at {start_time}",
                    data=event,
                )
            elif action == "list":
                events = calendar_repo.list_events(user_id)
                if not events:
                    return ToolResult(context="No upcoming events.")
                lines = [f"- {e['title']} at {e['start_time']}" for e in events]
                return ToolResult(context=f"Events ({len(events)}):\n" + "\n".join(lines))
            elif action == "delete" and event_id:
                if calendar_repo.delete_event(event_id, user_id):
                    return ToolResult(context="Event deleted.")
                return ToolResult(context="Event not found.")
            else:
                return ToolResult(context="Use action='create' with title+start_time, action='list', or action='delete' with event_id")
        except Exception as e:
            return ToolResult(error=f"Calendar operation failed: {e}")
