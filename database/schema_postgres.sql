-- ============================================================
-- Project Jarvis — PostgreSQL / MySQL Compatible Schema
-- ============================================================
-- Same structure as SQLite schema, adapted for production RDBMS.
-- For MySQL: change TEXT PRIMARY KEY → VARCHAR(36), TEXT → LONGTEXT where needed.
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id              VARCHAR(36) PRIMARY KEY,
    username        VARCHAR(100) UNIQUE,
    email           VARCHAR(255) UNIQUE,
    display_name    VARCHAR(255) NOT NULL DEFAULT '',
    avatar_url      TEXT DEFAULT '',
    password_hash   VARCHAR(255),
    auth_provider   VARCHAR(20) NOT NULL DEFAULT 'local',
    is_guest        BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at   TIMESTAMP
);

CREATE TABLE IF NOT EXISTS platform_identities (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform        VARCHAR(30) NOT NULL,
    platform_uid    VARCHAR(255) NOT NULL,
    platform_name   VARCHAR(255) DEFAULT '',
    metadata        TEXT DEFAULT '{}',
    linked_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, platform_uid)
);
CREATE INDEX IF NOT EXISTS idx_platform_user ON platform_identities(user_id);

CREATE TABLE IF NOT EXISTS conversations (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(500) DEFAULT '',
    platform        VARCHAR(30) NOT NULL DEFAULT 'web',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);

CREATE TABLE IF NOT EXISTS messages (
    id              VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,
    content         TEXT NOT NULL,
    signals_s       REAL,
    signals_d       REAL,
    signals_c       REAL,
    dominant_emotion VARCHAR(50),
    trust_level     REAL,
    metadata        TEXT DEFAULT '{}',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id);

CREATE TABLE IF NOT EXISTS user_facts (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category        VARCHAR(50) NOT NULL DEFAULT 'general',
    key             VARCHAR(255) NOT NULL,
    value           TEXT NOT NULL,
    confidence      REAL NOT NULL DEFAULT 1.0,
    source          VARCHAR(50) DEFAULT 'conversation',
    first_mentioned TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_confirmed  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    mention_count   INTEGER NOT NULL DEFAULT 1,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(user_id, category, key)
);
CREATE INDEX IF NOT EXISTS idx_facts_user ON user_facts(user_id);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id         VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pref_key        VARCHAR(100) NOT NULL,
    pref_value      TEXT NOT NULL,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, pref_key)
);

CREATE TABLE IF NOT EXISTS conversation_summaries (
    id              VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id         VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    summary         TEXT NOT NULL,
    key_topics      TEXT DEFAULT '[]',
    emotional_arc   TEXT DEFAULT '{}',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_summary_user ON conversation_summaries(user_id);

CREATE TABLE IF NOT EXISTS evc_snapshots (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id VARCHAR(36) REFERENCES conversations(id) ON DELETE SET NULL,
    turn            INTEGER NOT NULL,
    hormones        TEXT NOT NULL,
    emotions        TEXT NOT NULL,
    trust           REAL NOT NULL,
    memory_vector   TEXT DEFAULT '{}',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_evc_user ON evc_snapshots(user_id);
