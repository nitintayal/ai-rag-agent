-- Run this in Supabase SQL Editor (https://supabase.com/dashboard → SQL Editor)
-- Safe to run on a fresh project. For existing projects use the migration block at the bottom.

CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    name            TEXT,
    email           TEXT UNIQUE,
    password        TEXT,
    avatar_url      TEXT,
    auth_provider   TEXT NOT NULL DEFAULT 'local',
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    llm_provider    TEXT,
    llm_model       TEXT,
    llm_api_key     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id),
    title           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system', 'tool')),
    content         TEXT NOT NULL,
    tool_name       TEXT,
    tool_result     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);

CREATE TABLE IF NOT EXISTS journal_entries (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    title           TEXT,
    content         TEXT NOT NULL,
    mood            TEXT,
    tags            TEXT NOT NULL DEFAULT '[]',
    entry_date      TEXT NOT NULL,
    embedding       TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_journal_user ON journal_entries(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS tasks (
    id               TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL,
    title            TEXT NOT NULL,
    description      TEXT,
    due_date         TEXT,
    status           TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'done', 'cancelled')),
    priority         TEXT NOT NULL DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high')),
    recurrence       TEXT CHECK(recurrence IN ('daily', 'weekly', 'monthly')),
    reminder_sent_at TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id, status, due_date);

CREATE TABLE IF NOT EXISTS user_memories (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    key             TEXT NOT NULL,
    value           TEXT NOT NULL,
    category        TEXT NOT NULL DEFAULT 'general',
    embedding       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ,
    UNIQUE(user_id, key)
);
CREATE INDEX IF NOT EXISTS idx_memories_user ON user_memories(user_id);

CREATE TABLE IF NOT EXISTS calendar_events (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    start_time      TEXT NOT NULL,
    end_time        TEXT,
    all_day         BOOLEAN NOT NULL DEFAULT FALSE,
    location        TEXT,
    recurrence      TEXT CHECK(recurrence IN ('daily', 'weekly', 'monthly')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_calendar_user ON calendar_events(user_id, start_time);

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint    TEXT NOT NULL UNIQUE,
    p256dh      TEXT NOT NULL,
    auth        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_push_user ON push_subscriptions(user_id);

CREATE TABLE IF NOT EXISTS verification_codes (
    id              TEXT PRIMARY KEY,
    email           TEXT NOT NULL,
    code            TEXT NOT NULL,
    purpose         TEXT NOT NULL CHECK(purpose IN ('email_verify', 'password_reset')),
    expires_at      TIMESTAMPTZ NOT NULL,
    used            BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_verification_email ON verification_codes(email, purpose, used);

-- RLS (Row Level Security) — backend uses service_role key which bypasses RLS,
-- but enabling it protects against accidental anon key exposure.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_codes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all" ON users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON conversations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON messages FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON journal_entries FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON tasks FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON user_memories FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON calendar_events FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON push_subscriptions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON verification_codes FOR ALL USING (true) WITH CHECK (true);
