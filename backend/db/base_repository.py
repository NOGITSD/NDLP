"""
Abstract base repository — defines the interface for all DB backends.
Implementations: SQLiteRepository, FirebaseRepository, etc.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


# ── Data Transfer Objects ─────────────────────────────────────────────

@dataclass
class UserDTO:
    id: str
    username: Optional[str] = None
    email: Optional[str] = None
    display_name: str = ""
    avatar_url: str = ""
    password_hash: Optional[str] = None
    auth_provider: str = "local"          # local | google | guest
    is_guest: bool = False
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_login_at: Optional[str] = None


@dataclass
class PlatformIdentityDTO:
    id: str
    user_id: str
    platform: str          # line | discord | telegram | web
    platform_uid: str
    platform_name: str = ""
    metadata: str = "{}"
    linked_at: Optional[str] = None


@dataclass
class ConversationDTO:
    id: str
    user_id: str
    title: str = ""
    platform: str = "web"
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class MessageDTO:
    id: str
    conversation_id: str
    role: str              # user | assistant | system
    content: str = ""
    signals_s: Optional[float] = None
    signals_d: Optional[float] = None
    signals_c: Optional[float] = None
    dominant_emotion: Optional[str] = None
    trust_level: Optional[float] = None
    metadata: str = "{}"
    created_at: Optional[str] = None


@dataclass
class UserFactDTO:
    id: str
    user_id: str
    category: str = "general"
    key: str = ""
    value: str = ""
    confidence: float = 1.0
    source: str = "conversation"
    first_mentioned: Optional[str] = None
    last_confirmed: Optional[str] = None
    mention_count: int = 1
    is_active: bool = True


@dataclass
class UserPreferenceDTO:
    user_id: str
    pref_key: str
    pref_value: str
    updated_at: Optional[str] = None


@dataclass
class ConversationSummaryDTO:
    id: str
    conversation_id: str
    user_id: str
    summary: str = ""
    key_topics: str = "[]"
    emotional_arc: str = "{}"
    created_at: Optional[str] = None


@dataclass
class EVCSnapshotDTO:
    id: str
    user_id: str
    conversation_id: Optional[str] = None
    turn: int = 0
    hormones: str = "{}"
    emotions: str = "{}"
    trust: float = 0.5
    memory_vector: str = "{}"
    created_at: Optional[str] = None


# ── Abstract Repository ──────────────────────────────────────────────

class BaseRepository(abc.ABC):
    """All DB backends must implement this interface."""

    # ── Users ──

    @abc.abstractmethod
    def create_user(self, user: UserDTO) -> UserDTO: ...

    @abc.abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[UserDTO]: ...

    @abc.abstractmethod
    def get_user_by_username(self, username: str) -> Optional[UserDTO]: ...

    @abc.abstractmethod
    def get_user_by_email(self, email: str) -> Optional[UserDTO]: ...

    @abc.abstractmethod
    def update_user(self, user: UserDTO) -> UserDTO: ...

    @abc.abstractmethod
    def update_last_login(self, user_id: str) -> None: ...

    # ── Platform Identities ──

    @abc.abstractmethod
    def create_platform_identity(self, identity: PlatformIdentityDTO) -> PlatformIdentityDTO: ...

    @abc.abstractmethod
    def get_user_by_platform(self, platform: str, platform_uid: str) -> Optional[UserDTO]: ...

    @abc.abstractmethod
    def get_platform_identities(self, user_id: str) -> list[PlatformIdentityDTO]: ...

    # ── Conversations ──

    @abc.abstractmethod
    def create_conversation(self, conv: ConversationDTO) -> ConversationDTO: ...

    @abc.abstractmethod
    def get_conversation(self, conv_id: str) -> Optional[ConversationDTO]: ...

    @abc.abstractmethod
    def list_conversations(self, user_id: str, limit: int = 50) -> list[ConversationDTO]: ...

    @abc.abstractmethod
    def update_conversation(self, conv: ConversationDTO) -> ConversationDTO: ...

    # ── Messages ──

    @abc.abstractmethod
    def create_message(self, msg: MessageDTO) -> MessageDTO: ...

    @abc.abstractmethod
    def get_messages(self, conversation_id: str, limit: int = 100) -> list[MessageDTO]: ...

    @abc.abstractmethod
    def get_recent_messages(self, user_id: str, limit: int = 20) -> list[MessageDTO]: ...

    # ── User Facts (memory) ──

    @abc.abstractmethod
    def upsert_fact(self, fact: UserFactDTO) -> UserFactDTO: ...

    @abc.abstractmethod
    def get_facts(self, user_id: str, category: Optional[str] = None) -> list[UserFactDTO]: ...

    @abc.abstractmethod
    def delete_fact(self, fact_id: str) -> bool: ...

    # ── User Preferences ──

    @abc.abstractmethod
    def set_preference(self, pref: UserPreferenceDTO) -> UserPreferenceDTO: ...

    @abc.abstractmethod
    def get_preferences(self, user_id: str) -> list[UserPreferenceDTO]: ...

    @abc.abstractmethod
    def get_preference(self, user_id: str, pref_key: str) -> Optional[UserPreferenceDTO]: ...

    # ── Conversation Summaries ──

    @abc.abstractmethod
    def create_summary(self, summary: ConversationSummaryDTO) -> ConversationSummaryDTO: ...

    @abc.abstractmethod
    def get_summaries(self, user_id: str, limit: int = 20) -> list[ConversationSummaryDTO]: ...

    # ── EVC Snapshots ──

    @abc.abstractmethod
    def save_evc_snapshot(self, snapshot: EVCSnapshotDTO) -> EVCSnapshotDTO: ...

    @abc.abstractmethod
    def get_latest_evc_snapshot(self, user_id: str) -> Optional[EVCSnapshotDTO]: ...

    # ── Lifecycle ──

    @abc.abstractmethod
    def close(self) -> None: ...
