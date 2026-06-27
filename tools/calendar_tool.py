"""Calendar tool: simple event management backed by SQLite."""

from datetime import datetime, timezone
from uuid import uuid4

from tools.base import BaseTool, ToolDefinition, ToolResult
from storage.database import get_connection


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
                eid = str(uuid4())
                now = datetime.now(timezone.utc).isoformat()
                with get_connection() as conn:
                    conn.execute(
                        """INSERT INTO calendar_events (id, user_id, title, description, start_time, end_time, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (eid, user_id, title, description, start_time, end_time, now),
                    )
                return ToolResult(
                    context=f"Event created: '{title}' at {start_time}",
                    data={"id": eid, "title": title, "start_time": start_time},
                )
            elif action == "list":
                with get_connection() as conn:
                    rows = conn.execute(
                        """SELECT * FROM calendar_events WHERE user_id = ?
                           ORDER BY start_time ASC LIMIT 20""",
                        (user_id,),
                    ).fetchall()
                if not rows:
                    return ToolResult(context="No upcoming events.")
                lines = [f"- {r['title']} at {r['start_time']}" for r in rows]
                return ToolResult(context=f"Events ({len(rows)}):\n" + "\n".join(lines))
            elif action == "delete" and event_id:
                with get_connection() as conn:
                    cursor = conn.execute(
                        "DELETE FROM calendar_events WHERE id = ? AND user_id = ?",
                        (event_id, user_id),
                    )
                if cursor.rowcount > 0:
                    return ToolResult(context="Event deleted.")
                return ToolResult(context="Event not found.")
            else:
                return ToolResult(context="Use action='create' with title+start_time, action='list', or action='delete' with event_id")
        except Exception as e:
            return ToolResult(error=f"Calendar operation failed: {e}")
