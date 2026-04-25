import json
from datetime import date, datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

from embeddings.sentence_embeddings import embed_query
from journal.schemas import JournalEntryCreate, JournalEntryUpdate


class PostgresJournalStore:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._ensure_tables()

    def _get_connection(self):
        return psycopg2.connect(self.database_url)

    def _ensure_tables(self):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS journal_entries (
            id UUID PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            mood TEXT,
            tags JSONB NOT NULL DEFAULT '[]'::jsonb,
            entry_date DATE NOT NULL,
            embedding JSONB NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NULL
        );

        CREATE INDEX IF NOT EXISTS idx_journal_entries_user_id
        ON journal_entries (user_id);

        CREATE INDEX IF NOT EXISTS idx_journal_entries_entry_date
        ON journal_entries (entry_date DESC);

        ALTER TABLE journal_entries
        ALTER COLUMN updated_at DROP NOT NULL;

        CREATE OR REPLACE FUNCTION preserve_journal_created_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.created_at = OLD.created_at;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_preserve_journal_created_at
        ON journal_entries;

        CREATE TRIGGER trg_preserve_journal_created_at
        BEFORE UPDATE ON journal_entries
        FOR EACH ROW
        EXECUTE FUNCTION preserve_journal_created_at();
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_table_sql)

    def list_entries(self, user_id: str, limit: int = 20, offset: int = 0) -> Dict:
        entries_query = """
        SELECT id, user_id, title, content, mood, tags, entry_date, created_at, updated_at
        FROM journal_entries
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """
        count_query = """
        SELECT COUNT(*) AS total
        FROM journal_entries
        WHERE user_id = %s
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(count_query, (user_id,))
                total = cur.fetchone()["total"]
                cur.execute(entries_query, (user_id, limit, offset))
                rows = cur.fetchall()

        items = [self._serialize_row(row) for row in rows]
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total,
        }

    def get_entry(self, entry_id: str, user_id: str) -> Optional[Dict]:
        query = """
        SELECT id, user_id, title, content, mood, tags, entry_date, created_at, updated_at
        FROM journal_entries
        WHERE id = %s AND user_id = %s
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (entry_id, user_id))
                row = cur.fetchone()
        return self._serialize_row(row) if row else None

    def add_entry(self, payload: JournalEntryCreate) -> Dict:
        now = datetime.now(timezone.utc)
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
        embedding = embed_query(self._search_text(entry)).tolist()

        insert_sql = """
        INSERT INTO journal_entries (
            id, user_id, title, content, mood, tags, entry_date, embedding, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s)
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    insert_sql,
                    (
                        entry_id,
                        payload.user_id,
                        payload.title,
                        payload.content,
                        payload.mood,
                        json.dumps(payload.tags),
                        entry_date,
                        json.dumps(embedding),
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

        embedding = embed_query(self._search_text(updated_entry)).tolist()
        update_sql = """
        UPDATE journal_entries
        SET title = %s,
            content = %s,
            mood = %s,
            tags = %s::jsonb,
            entry_date = %s,
            embedding = %s::jsonb,
            created_at = journal_entries.created_at,
            updated_at = NOW()
        WHERE id = %s AND user_id = %s
        RETURNING id, user_id, title, content, mood, tags, entry_date, created_at, updated_at
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    update_sql,
                    (
                        updated_entry["title"],
                        updated_entry["content"],
                        updated_entry["mood"],
                        json.dumps(updated_entry["tags"]),
                        updated_entry["entry_date"],
                        json.dumps(embedding),
                        entry_id,
                        user_id,
                    ),
                )
                row = cur.fetchone()
        return self._serialize_row(row) if row else None

    def delete_entry(self, entry_id: str, user_id: str) -> bool:
        delete_sql = """
        DELETE FROM journal_entries
        WHERE id = %s AND user_id = %s
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(delete_sql, (entry_id, user_id))
                deleted = cur.rowcount > 0
        return deleted

    def search_entries(self, user_id: str, query: str, k: int = 5) -> List[Dict]:
        select_sql = """
        SELECT id, user_id, title, content, mood, tags, entry_date, embedding, created_at, updated_at
        FROM journal_entries
        WHERE user_id = %s
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(select_sql, (user_id,))
                rows = cur.fetchall()

        if not rows:
            return []

        query_vector = np.array(embed_query(query), dtype="float32")
        scored_results = []
        for row in rows:
            embedding = np.array(row["embedding"], dtype="float32")
            score = float(np.dot(query_vector, embedding))
            scored_results.append({"entry": self._serialize_row(row), "score": score})

        scored_results.sort(key=lambda item: item["score"], reverse=True)
        return scored_results[:k]

    @staticmethod
    def _serialize_row(row: Dict) -> Dict:
        if row is None:
            return None
        serialized = dict(row)
        serialized["id"] = str(serialized["id"])
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
