import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

import numpy as np

from embeddings.sentence_embeddings import embed_query
from journal.schemas import JournalEntryCreate, JournalEntryUpdate


class SqliteJournalStore:
    def __init__(self, database_path: str):
        self.database_path = database_path
        self._ensure_tables()

    def _get_connection(self):
        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self):
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS journal_entries (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    content TEXT NOT NULL,
                    mood TEXT,
                    tags TEXT NOT NULL,
                    entry_date TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_journal_entries_user_id ON journal_entries (user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_journal_entries_entry_date ON journal_entries (entry_date DESC)"
            )

    def list_entries(self, user_id: str, limit: int = 20, offset: int = 0) -> Dict:
        with self._get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM journal_entries WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]
            rows = conn.execute(
                """
                SELECT id, user_id, title, content, mood, tags, entry_date, created_at, updated_at
                FROM journal_entries
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset),
            ).fetchall()

        items = [self._serialize_row(row) for row in rows]
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total,
        }

    def get_entry(self, entry_id: str, user_id: str) -> Optional[Dict]:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, user_id, title, content, mood, tags, entry_date, created_at, updated_at
                FROM journal_entries
                WHERE id = ? AND user_id = ?
                """,
                (entry_id, user_id),
            ).fetchone()
        return self._serialize_row(row) if row else None

    def add_entry(self, payload: JournalEntryCreate) -> Dict:
        now = datetime.now(timezone.utc).isoformat()
        entry_date = payload.entry_date or date.today()
        entry_id = str(uuid4())
        entry = {
            "id": entry_id,
            "user_id": payload.user_id,
            "title": payload.title,
            "content": payload.content,
            "mood": payload.mood,
            "tags": payload.tags,
            "entry_date": str(entry_date),
            "created_at": now,
            "updated_at": None,
        }
        embedding = json.dumps(embed_query(self._search_text(entry)).tolist())

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO journal_entries (
                    id, user_id, title, content, mood, tags, entry_date, embedding, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    payload.user_id,
                    payload.title,
                    payload.content,
                    payload.mood,
                    json.dumps(payload.tags),
                    str(entry_date),
                    embedding,
                    now,
                    None,
                ),
            )
        return entry

    def update_entry(
        self, entry_id: str, user_id: str, payload: JournalEntryUpdate
    ) -> Optional[Dict]:
        current_entry = self.get_entry(entry_id=entry_id, user_id=user_id)
        if current_entry is None:
            return None

        updated_entry = dict(current_entry)
        for field, value in payload.model_dump(exclude_unset=True).items():
            if field in {"content", "tags", "entry_date"} and value is None:
                continue
            updated_entry[field] = value

        updated_at = datetime.now(timezone.utc).isoformat()
        embedding = json.dumps(embed_query(self._search_text(updated_entry)).tolist())
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE journal_entries
                SET title = ?,
                    content = ?,
                    mood = ?,
                    tags = ?,
                    entry_date = ?,
                    embedding = ?,
                    updated_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (
                    updated_entry["title"],
                    updated_entry["content"],
                    updated_entry["mood"],
                    json.dumps(updated_entry["tags"]),
                    str(updated_entry["entry_date"]),
                    embedding,
                    updated_at,
                    entry_id,
                    user_id,
                ),
            )
        return self.get_entry(entry_id=entry_id, user_id=user_id)

    def delete_entry(self, entry_id: str, user_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM journal_entries WHERE id = ? AND user_id = ?",
                (entry_id, user_id),
            )
        return cursor.rowcount > 0

    def search_entries(self, user_id: str, query: str, k: int = 5) -> List[Dict]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, title, content, mood, tags, entry_date, embedding, created_at, updated_at
                FROM journal_entries
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchall()

        if not rows:
            return []

        query_vector = np.array(embed_query(query), dtype="float32")
        results = []
        for row in rows:
            serialized = self._serialize_row(row)
            embedding = np.array(json.loads(row["embedding"]), dtype="float32")
            score = float(np.dot(query_vector, embedding))
            results.append({"entry": serialized, "score": score})

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:k]

    @staticmethod
    def _serialize_row(row: sqlite3.Row) -> Dict:
        serialized = dict(row)
        serialized["tags"] = json.loads(serialized["tags"]) if serialized["tags"] else []
        serialized["entry_date"] = str(serialized["entry_date"])
        return serialized

    @staticmethod
    def _search_text(entry: Dict) -> str:
        tags = " ".join(entry.get("tags", []))
        return "\n".join(
            part
            for part in [
                entry.get("title") or "",
                entry.get("content") or "",
                entry.get("mood") or "",
                tags,
            ]
            if part
        )
