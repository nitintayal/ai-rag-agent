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
                description: str | None = None, location: str | None = None,
                all_day: bool = False, recurrence: str | None = None,
                event_id: str | None = None, start: str | None = None,
                end: str | None = None, **kwargs) -> ToolResult:
        try:
            if action == "create" and title and start_time:
                event = calendar_repo.create_event(
                    user_id, title, start_time, end_time, description,
                    location=location, all_day=all_day, recurrence=recurrence,
                )
                return ToolResult(
                    context=f"Event created: '{title}' at {start_time}" + (f" @ {location}" if location else ""),
                    data=event,
                )
            elif action == "list":
                events = calendar_repo.list_events(user_id, start=start, end=end)
                if not events:
                    return ToolResult(context="No upcoming events.")
                lines = [f"- {e['title']} at {e['start_time']}" + (f" @ {e.get('location','')}" if e.get('location') else "") for e in events]
                return ToolResult(context=f"Events ({len(events)}):\n" + "\n".join(lines))
            elif action == "update" and event_id:
                fields = {k: v for k, v in {
                    "title": title or None, "start_time": start_time or None,
                    "end_time": end_time, "description": description,
                    "location": location, "all_day": all_day if all_day else None,
                    "recurrence": recurrence,
                }.items() if v is not None}
                updated = calendar_repo.update_event(event_id, user_id, **fields)
                if updated:
                    return ToolResult(context=f"Event updated: '{updated['title']}'", data=updated)
                return ToolResult(context="Event not found.")
            elif action == "delete" and event_id:
                if calendar_repo.delete_event(event_id, user_id):
                    return ToolResult(context="Event deleted.")
                return ToolResult(context="Event not found.")
            else:
                return ToolResult(context="Use action='create' with title+start_time, action='list', action='update' with event_id, or action='delete' with event_id")
        except Exception as e:
            return ToolResult(error=f"Calendar operation failed: {e}")
