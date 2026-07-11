"""Export any backend's data to a portable SQLite file."""

import sqlite3
import tempfile
from datetime import datetime


# Tables to export in dependency order (parents before children)
_TABLES = [
    "users",
    "conversations",
    "messages",
    "journal_entries",
    "tasks",
    "user_memories",
    "verification_codes",
    "push_subscriptions",
    "calendar_events",
]


def _fetch_all(backend_name: str) -> dict[str, list[dict]]:
    """Fetch all rows from every table using the active backend's connection."""
    data = {}

    if backend_name == "sqlite":
        from storage.database import get_connection
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            for table in _TABLES:
                try:
                    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                    data[table] = [dict(r) for r in rows]
                except Exception:
                    data[table] = []

    elif backend_name == "supabase":
        from storage.backends.supabase.client import get_supabase
        sb = get_supabase()
        for table in _TABLES:
            try:
                result = sb.table(table).select("*").execute()
                data[table] = result.data or []
            except Exception:
                data[table] = []

    else:
        raise ValueError(f"Export not supported for backend: {backend_name}")

    return data


def export_to_sqlite() -> str:
    """
    Export all data from the active backend into a temp SQLite file.
    Returns the path to the SQLite file.
    """
    from configs.config import settings
    from storage.database import _SCHEMA

    # Strip ALTER TABLE migration lines — only needed for existing DBs, not fresh exports
    clean_schema = "\n".join(
        line for line in _SCHEMA.splitlines()
        if not line.strip().upper().startswith("ALTER TABLE")
    )

    data = _fetch_all(settings.DB_BACKEND)

    tmp = tempfile.NamedTemporaryFile(
        suffix=".db",
        prefix=f"assistant_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_",
        delete=False,
    )
    tmp.close()

    conn = sqlite3.connect(tmp.name)
    conn.executescript(clean_schema)

    for table, rows in data.items():
        if not rows:
            continue
        cols = list(rows[0].keys())
        placeholders = ", ".join("?" * len(cols))
        col_names = ", ".join(cols)
        conn.executemany(
            f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})",
            [tuple(row.get(c) for c in cols) for row in rows],
        )

    conn.commit()
    conn.close()

    return tmp.name
