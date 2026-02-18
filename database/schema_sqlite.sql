-- ============================================================
-- Project Jarvis — SQLite Schema
-- ============================================================
-- Supports: auth, user profiles, conversations, user memory,
--           platform identities (LINE/Discord), EVC snapshots.
-- ============================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ────────────────────────────────────────────
-- USERS
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,           -- UUID
    username        TEXT UNIQUE,                -- nullable for guest
    email           TEXT UNIQUE,                -- nullable for guest
    display_name    TEXT NOT NULL DEFAULT '',
    avatar_url      TEXT DEFAULT '',
    password_hash   TEXT,                       -- bcrypt hash, null for OAuth/guest
    auth_provider   TEXT NOT NULL DEFAULT 'local',  -- local | google | guest
    is_guest        INTEGER NOT NULL DEFAULT 0,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    last_login_at   TEXT
);

-- ────────────────────────────────────────────
-- PLATFORM IDENTITIES (LINE, Discord, etc.)
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS platform_identities (
    id              TEXT PRIMARY KEY,           -- UUID
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform        TEXT NOT NULL,              -- 'line' | 'discord' | 'telegram' | 'web'
    platform_uid    TEXT NOT NULL,              -- platform-specific user ID
    platform_name   TEXT DEFAULT '',
    metadata        TEXT DEFAULT '{}',          -- JSON extra data
    linked_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(platform, platform_uid)
);
CREATE INDEX IF NOT EXISTS idx_platform_user ON platform_identities(user_id);
CREATE INDEX IF NOT EXISTS idx_platform_lookup ON platform_identities(platform, platform_uid);

-- ────────────────────────────────────────────
-- SESSIONS / CONVERSATIONS
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversations (
    id              TEXT PRIMARY KEY,           -- UUID
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           TEXT DEFAULT '',
    platform        TEXT NOT NULL DEFAULT 'web',
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);

-- ────────────────────────────────────────────
-- MESSAGES
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,           -- UUID
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,              -- 'user' | 'assistant' | 'system'
    content         TEXT NOT NULL,
    signals_s       REAL,
    signals_d       REAL,
    signals_c       REAL,
    dominant_emotion TEXT,
    trust_level     REAL,
    metadata        TEXT DEFAULT '{}',          -- JSON (matched_skill, memory_used, etc.)
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_msg_time ON messages(created_at);

-- ────────────────────────────────────────────
-- USER MEMORY — Facts the bot learns about the user
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_facts (
    id              TEXT PRIMARY KEY,           -- UUID
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category        TEXT NOT NULL DEFAULT 'general',  -- 'personal' | 'preference' | 'work' | 'general'
    key             TEXT NOT NULL,              -- e.g. 'name', 'favorite_food', 'job'
    value           TEXT NOT NULL,
    confidence      REAL NOT NULL DEFAULT 1.0,  -- 0-1, how sure we are
    source          TEXT DEFAULT 'conversation', -- 'conversation' | 'explicit' | 'inferred'
    first_mentioned TEXT NOT NULL DEFAULT (datetime('now')),
    last_confirmed  TEXT NOT NULL DEFAULT (datetime('now')),
    mention_count   INTEGER NOT NULL DEFAULT 1,
    is_active       INTEGER NOT NULL DEFAULT 1,
    UNIQUE(user_id, category, key)
);
CREATE INDEX IF NOT EXISTS idx_facts_user ON user_facts(user_id);
CREATE INDEX IF NOT EXISTS idx_facts_category ON user_facts(user_id, category);

-- ────────────────────────────────────────────
-- USER PREFERENCES — Bot behavior customization
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pref_key        TEXT NOT NULL,              -- 'language', 'formality', 'personality', etc.
    pref_value      TEXT NOT NULL,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, pref_key)
);

-- ────────────────────────────────────────────
-- CONVERSATION SUMMARIES — Compressed memory per conversation
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    summary         TEXT NOT NULL,
    key_topics      TEXT DEFAULT '[]',          -- JSON array of topic strings
    emotional_arc   TEXT DEFAULT '{}',          -- JSON { start_emotion, end_emotion, trust_delta }
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_summary_user ON conversation_summaries(user_id);

-- ────────────────────────────────────────────
-- EVC SNAPSHOTS — Periodic emotional state saves
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS evc_snapshots (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id TEXT REFERENCES conversations(id) ON DELETE SET NULL,
    turn            INTEGER NOT NULL,
    hormones        TEXT NOT NULL,              -- JSON { Dopamine: 0.5, ... }
    emotions        TEXT NOT NULL,              -- JSON { Joy: 0.3, ... }
    trust           REAL NOT NULL,
    memory_vector   TEXT DEFAULT '{}',          -- JSON
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_evc_user ON evc_snapshots(user_id);
