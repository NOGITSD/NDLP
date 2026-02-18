"""
SQLite implementation of BaseRepository.
Default local DB — zero config, works everywhere.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .base_repository import (
    BaseRepository, UserDTO, PlatformIdentityDTO, ConversationDTO,
    MessageDTO, UserFactDTO, UserPreferenceDTO, ConversationSummaryDTO,
    EVCSnapshotDTO,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteRepository(BaseRepository):
    def __init__(self, db_path: str = "data/jarvis.db"):
        p = Path(db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(p), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self):
        schema_path = Path(__file__).resolve().parents[2] / "database" / "schema_sqlite.sql"
        if schema_path.exists():
            self._db.executescript(schema_path.read_text(encoding="utf-8"))
        else:
            raise FileNotFoundError(f"Schema not found: {schema_path}")

    def _exec(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self._db.execute(sql, params)

    def _commit(self):
        self._db.commit()

    # ── Users ──

    def create_user(self, user: UserDTO) -> UserDTO:
        now = _now_iso()
        user.created_at = user.created_at or now
        user.updated_at = now
        self._exec(
            """INSERT INTO users (id, username, email, display_name, avatar_url,
               password_hash, auth_provider, is_guest, is_active, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (user.id, user.username, user.email, user.display_name, user.avatar_url,
             user.password_hash, user.auth_provider, int(user.is_guest), int(user.is_active),
             user.created_at, user.updated_at),
        )
        self._commit()
        return user

    def _row_to_user(self, row) -> UserDTO:
        return UserDTO(
            id=row["id"], username=row["username"], email=row["email"],
            display_name=row["display_name"], avatar_url=row["avatar_url"] or "",
            password_hash=row["password_hash"], auth_provider=row["auth_provider"],
            is_guest=bool(row["is_guest"]), is_active=bool(row["is_active"]),
            created_at=row["created_at"], updated_at=row["updated_at"],
            last_login_at=row["last_login_at"],
        )

    def get_user_by_id(self, user_id: str) -> Optional[UserDTO]:
        row = self._exec("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return self._row_to_user(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[UserDTO]:
        row = self._exec("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return self._row_to_user(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[UserDTO]:
        row = self._exec("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return self._row_to_user(row) if row else None

    def update_user(self, user: UserDTO) -> UserDTO:
        user.updated_at = _now_iso()
        self._exec(
            """UPDATE users SET username=?, email=?, display_name=?, avatar_url=?,
               password_hash=?, auth_provider=?, is_guest=?, is_active=?, updated_at=?
               WHERE id=?""",
            (user.username, user.email, user.display_name, user.avatar_url,
             user.password_hash, user.auth_provider, int(user.is_guest), int(user.is_active),
             user.updated_at, user.id),
        )
        self._commit()
        return user

    def update_last_login(self, user_id: str) -> None:
        now = _now_iso()
        self._exec("UPDATE users SET last_login_at=?, updated_at=? WHERE id=?", (now, now, user_id))
        self._commit()

    # ── Platform Identities ──

    def create_platform_identity(self, identity: PlatformIdentityDTO) -> PlatformIdentityDTO:
        identity.linked_at = identity.linked_at or _now_iso()
        self._exec(
            """INSERT INTO platform_identities (id, user_id, platform, platform_uid, platform_name, metadata, linked_at)
               VALUES (?,?,?,?,?,?,?)""",
            (identity.id, identity.user_id, identity.platform, identity.platform_uid,
             identity.platform_name, identity.metadata, identity.linked_at),
        )
        self._commit()
        return identity

    def get_user_by_platform(self, platform: str, platform_uid: str) -> Optional[UserDTO]:
        row = self._exec(
            """SELECT u.* FROM users u JOIN platform_identities p ON u.id=p.user_id
               WHERE p.platform=? AND p.platform_uid=?""",
            (platform, platform_uid),
        ).fetchone()
        return self._row_to_user(row) if row else None

    def get_platform_identities(self, user_id: str) -> list[PlatformIdentityDTO]:
        rows = self._exec("SELECT * FROM platform_identities WHERE user_id=?", (user_id,)).fetchall()
        return [PlatformIdentityDTO(
            id=r["id"], user_id=r["user_id"], platform=r["platform"],
            platform_uid=r["platform_uid"], platform_name=r["platform_name"],
            metadata=r["metadata"], linked_at=r["linked_at"],
        ) for r in rows]

    # ── Conversations ──

    def create_conversation(self, conv: ConversationDTO) -> ConversationDTO:
        now = _now_iso()
        conv.created_at = conv.created_at or now
        conv.updated_at = now
        self._exec(
            """INSERT INTO conversations (id, user_id, title, platform, is_active, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?)""",
            (conv.id, conv.user_id, conv.title, conv.platform, int(conv.is_active),
             conv.created_at, conv.updated_at),
        )
        self._commit()
        return conv

    def get_conversation(self, conv_id: str) -> Optional[ConversationDTO]:
        row = self._exec("SELECT * FROM conversations WHERE id=?", (conv_id,)).fetchone()
        if not row:
            return None
        return ConversationDTO(
            id=row["id"], user_id=row["user_id"], title=row["title"],
            platform=row["platform"], is_active=bool(row["is_active"]),
            created_at=row["created_at"], updated_at=row["updated_at"],
        )

    def list_conversations(self, user_id: str, limit: int = 50) -> list[ConversationDTO]:
        rows = self._exec(
            "SELECT * FROM conversations WHERE user_id=? ORDER BY updated_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [ConversationDTO(
            id=r["id"], user_id=r["user_id"], title=r["title"],
            platform=r["platform"], is_active=bool(r["is_active"]),
            created_at=r["created_at"], updated_at=r["updated_at"],
        ) for r in rows]

    def update_conversation(self, conv: ConversationDTO) -> ConversationDTO:
        conv.updated_at = _now_iso()
        self._exec(
            "UPDATE conversations SET title=?, is_active=?, updated_at=? WHERE id=?",
            (conv.title, int(conv.is_active), conv.updated_at, conv.id),
        )
        self._commit()
        return conv

    # ── Messages ──

    def create_message(self, msg: MessageDTO) -> MessageDTO:
        msg.created_at = msg.created_at or _now_iso()
        self._exec(
            """INSERT INTO messages (id, conversation_id, role, content,
               signals_s, signals_d, signals_c, dominant_emotion, trust_level, metadata, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (msg.id, msg.conversation_id, msg.role, msg.content,
             msg.signals_s, msg.signals_d, msg.signals_c,
             msg.dominant_emotion, msg.trust_level, msg.metadata, msg.created_at),
        )
        self._commit()
        # Update conversation updated_at
        self._exec(
            "UPDATE conversations SET updated_at=? WHERE id=?",
            (_now_iso(), msg.conversation_id),
        )
        self._commit()
        return msg

    def get_messages(self, conversation_id: str, limit: int = 100) -> list[MessageDTO]:
        rows = self._exec(
            "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at ASC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
        return [MessageDTO(
            id=r["id"], conversation_id=r["conversation_id"], role=r["role"],
            content=r["content"], signals_s=r["signals_s"], signals_d=r["signals_d"],
            signals_c=r["signals_c"], dominant_emotion=r["dominant_emotion"],
            trust_level=r["trust_level"], metadata=r["metadata"], created_at=r["created_at"],
        ) for r in rows]

    def get_recent_messages(self, user_id: str, limit: int = 20) -> list[MessageDTO]:
        rows = self._exec(
            """SELECT m.* FROM messages m
               JOIN conversations c ON m.conversation_id=c.id
               WHERE c.user_id=? ORDER BY m.created_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        return [MessageDTO(
            id=r["id"], conversation_id=r["conversation_id"], role=r["role"],
            content=r["content"], signals_s=r["signals_s"], signals_d=r["signals_d"],
            signals_c=r["signals_c"], dominant_emotion=r["dominant_emotion"],
            trust_level=r["trust_level"], metadata=r["metadata"], created_at=r["created_at"],
        ) for r in rows]

    # ── User Facts (memory) ──

    def upsert_fact(self, fact: UserFactDTO) -> UserFactDTO:
        now = _now_iso()
        fact.first_mentioned = fact.first_mentioned or now
        fact.last_confirmed = now
        existing = self._exec(
            "SELECT id, mention_count FROM user_facts WHERE user_id=? AND category=? AND key=?",
            (fact.user_id, fact.category, fact.key),
        ).fetchone()
        if existing:
            self._exec(
                """UPDATE user_facts SET value=?, confidence=?, source=?, last_confirmed=?,
                   mention_count=mention_count+1, is_active=? WHERE id=?""",
                (fact.value, fact.confidence, fact.source, now, int(fact.is_active), existing["id"]),
            )
            fact.id = existing["id"]
            fact.mention_count = existing["mention_count"] + 1
        else:
            self._exec(
                """INSERT INTO user_facts (id, user_id, category, key, value, confidence, source,
                   first_mentioned, last_confirmed, mention_count, is_active)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (fact.id, fact.user_id, fact.category, fact.key, fact.value,
                 fact.confidence, fact.source, fact.first_mentioned, fact.last_confirmed,
                 fact.mention_count, int(fact.is_active)),
            )
        self._commit()
        return fact

    def get_facts(self, user_id: str, category: Optional[str] = None) -> list[UserFactDTO]:
        if category:
            rows = self._exec(
                "SELECT * FROM user_facts WHERE user_id=? AND category=? AND is_active=1 ORDER BY last_confirmed DESC",
                (user_id, category),
            ).fetchall()
        else:
            rows = self._exec(
                "SELECT * FROM user_facts WHERE user_id=? AND is_active=1 ORDER BY last_confirmed DESC",
                (user_id,),
            ).fetchall()
        return [UserFactDTO(
            id=r["id"], user_id=r["user_id"], category=r["category"],
            key=r["key"], value=r["value"], confidence=r["confidence"],
            source=r["source"], first_mentioned=r["first_mentioned"],
            last_confirmed=r["last_confirmed"], mention_count=r["mention_count"],
            is_active=bool(r["is_active"]),
        ) for r in rows]

    def delete_fact(self, fact_id: str) -> bool:
        cur = self._exec("UPDATE user_facts SET is_active=0 WHERE id=?", (fact_id,))
        self._commit()
        return cur.rowcount > 0

    # ── User Preferences ──

    def set_preference(self, pref: UserPreferenceDTO) -> UserPreferenceDTO:
        pref.updated_at = _now_iso()
        self._exec(
            "INSERT OR REPLACE INTO user_preferences (user_id, pref_key, pref_value, updated_at) VALUES (?,?,?,?)",
            (pref.user_id, pref.pref_key, pref.pref_value, pref.updated_at),
        )
        self._commit()
        return pref

    def get_preferences(self, user_id: str) -> list[UserPreferenceDTO]:
        rows = self._exec("SELECT * FROM user_preferences WHERE user_id=?", (user_id,)).fetchall()
        return [UserPreferenceDTO(
            user_id=r["user_id"], pref_key=r["pref_key"],
            pref_value=r["pref_value"], updated_at=r["updated_at"],
        ) for r in rows]

    def get_preference(self, user_id: str, pref_key: str) -> Optional[UserPreferenceDTO]:
        row = self._exec(
            "SELECT * FROM user_preferences WHERE user_id=? AND pref_key=?",
            (user_id, pref_key),
        ).fetchone()
        if not row:
            return None
        return UserPreferenceDTO(
            user_id=row["user_id"], pref_key=row["pref_key"],
            pref_value=row["pref_value"], updated_at=row["updated_at"],
        )

    # ── Conversation Summaries ──

    def create_summary(self, summary: ConversationSummaryDTO) -> ConversationSummaryDTO:
        summary.created_at = summary.created_at or _now_iso()
        self._exec(
            """INSERT INTO conversation_summaries (id, conversation_id, user_id, summary, key_topics, emotional_arc, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (summary.id, summary.conversation_id, summary.user_id, summary.summary,
             summary.key_topics, summary.emotional_arc, summary.created_at),
        )
        self._commit()
        return summary

    def get_summaries(self, user_id: str, limit: int = 20) -> list[ConversationSummaryDTO]:
        rows = self._exec(
            "SELECT * FROM conversation_summaries WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [ConversationSummaryDTO(
            id=r["id"], conversation_id=r["conversation_id"], user_id=r["user_id"],
            summary=r["summary"], key_topics=r["key_topics"],
            emotional_arc=r["emotional_arc"], created_at=r["created_at"],
        ) for r in rows]

    # ── EVC Snapshots ──

    def save_evc_snapshot(self, snapshot: EVCSnapshotDTO) -> EVCSnapshotDTO:
        snapshot.created_at = snapshot.created_at or _now_iso()
        self._exec(
            """INSERT INTO evc_snapshots (id, user_id, conversation_id, turn, hormones, emotions, trust, memory_vector, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (snapshot.id, snapshot.user_id, snapshot.conversation_id, snapshot.turn,
             snapshot.hormones, snapshot.emotions, snapshot.trust,
             snapshot.memory_vector, snapshot.created_at),
        )
        self._commit()
        return snapshot

    def get_latest_evc_snapshot(self, user_id: str) -> Optional[EVCSnapshotDTO]:
        row = self._exec(
            "SELECT * FROM evc_snapshots WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return EVCSnapshotDTO(
            id=row["id"], user_id=row["user_id"],
            conversation_id=row["conversation_id"], turn=row["turn"],
            hormones=row["hormones"], emotions=row["emotions"],
            trust=row["trust"], memory_vector=row["memory_vector"],
            created_at=row["created_at"],
        )

    # ── Lifecycle ──

    def close(self) -> None:
        self._db.close()
