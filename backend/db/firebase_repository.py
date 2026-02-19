"""
Firebase Firestore implementation of BaseRepository.
Cloud DB option — requires firebase-admin SDK and service account key.

Usage:
  1. pip install firebase-admin
  2. Set FIREBASE_CREDENTIALS env var to path of service account JSON
  3. Set DB_BACKEND=firebase in .env
"""

from __future__ import annotations

import json
import os
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


def _get_firestore():
    """Lazy-init Firestore client."""
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        cred_path = os.getenv("FIREBASE_CREDENTIALS") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        cred_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")

        if cred_path:
            p = Path(cred_path)
            if not p.is_absolute():
                # Resolve relative to backend/ directory
                backend_dir = Path(__file__).resolve().parents[1]
                p = backend_dir / p
            if not p.exists():
                raise RuntimeError(
                    f"Firebase credential file not found: {p}. "
                    "Set FIREBASE_CREDENTIALS to a valid service-account JSON path."
                )
            cred = credentials.Certificate(str(p))
        elif cred_json:
            try:
                cred = credentials.Certificate(json.loads(cred_json))
            except Exception as e:
                raise RuntimeError("Invalid FIREBASE_SERVICE_ACCOUNT_JSON format") from e
        else:
            raise RuntimeError(
                "Firebase backend requires credentials. Set FIREBASE_CREDENTIALS, "
                "GOOGLE_APPLICATION_CREDENTIALS, or FIREBASE_SERVICE_ACCOUNT_JSON."
            )

        firebase_admin.initialize_app(cred)
    return firestore.client()


class FirebaseRepository(BaseRepository):
    """
    Firestore document structure:
      users/{user_id}
      users/{user_id}/platform_identities/{id}
      conversations/{conv_id}
      conversations/{conv_id}/messages/{msg_id}
      users/{user_id}/facts/{fact_id}
      users/{user_id}/preferences/{pref_key}
      users/{user_id}/summaries/{summary_id}
      users/{user_id}/evc_snapshots/{snapshot_id}
    """

    def __init__(self):
        self._db = _get_firestore()

    # ── Users ──

    def create_user(self, user: UserDTO) -> UserDTO:
        now = _now_iso()
        user.created_at = user.created_at or now
        user.updated_at = now
        doc = {
            "username": user.username, "email": user.email,
            "display_name": user.display_name, "avatar_url": user.avatar_url,
            "password_hash": user.password_hash, "auth_provider": user.auth_provider,
            "is_guest": user.is_guest, "is_active": user.is_active,
            "created_at": user.created_at, "updated_at": user.updated_at,
            "last_login_at": user.last_login_at,
        }
        self._db.collection("users").document(user.id).set(doc)
        return user

    def _doc_to_user(self, doc_id: str, data: dict) -> UserDTO:
        return UserDTO(
            id=doc_id, username=data.get("username"),
            email=data.get("email"), display_name=data.get("display_name", ""),
            avatar_url=data.get("avatar_url", ""),
            password_hash=data.get("password_hash"),
            auth_provider=data.get("auth_provider", "local"),
            is_guest=data.get("is_guest", False),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            last_login_at=data.get("last_login_at"),
        )

    def get_user_by_id(self, user_id: str) -> Optional[UserDTO]:
        doc = self._db.collection("users").document(user_id).get()
        if not doc.exists:
            return None
        return self._doc_to_user(doc.id, doc.to_dict())

    def get_user_by_username(self, username: str) -> Optional[UserDTO]:
        docs = self._db.collection("users").where("username", "==", username).limit(1).stream()
        for doc in docs:
            return self._doc_to_user(doc.id, doc.to_dict())
        return None

    def get_user_by_email(self, email: str) -> Optional[UserDTO]:
        docs = self._db.collection("users").where("email", "==", email).limit(1).stream()
        for doc in docs:
            return self._doc_to_user(doc.id, doc.to_dict())
        return None

    def update_user(self, user: UserDTO) -> UserDTO:
        user.updated_at = _now_iso()
        self._db.collection("users").document(user.id).update({
            "username": user.username, "email": user.email,
            "display_name": user.display_name, "avatar_url": user.avatar_url,
            "password_hash": user.password_hash, "auth_provider": user.auth_provider,
            "is_guest": user.is_guest, "is_active": user.is_active,
            "updated_at": user.updated_at,
        })
        return user

    def update_last_login(self, user_id: str) -> None:
        now = _now_iso()
        self._db.collection("users").document(user_id).update({
            "last_login_at": now, "updated_at": now,
        })

    # ── Platform Identities ──

    def create_platform_identity(self, identity: PlatformIdentityDTO) -> PlatformIdentityDTO:
        identity.linked_at = identity.linked_at or _now_iso()
        doc = {
            "user_id": identity.user_id, "platform": identity.platform,
            "platform_uid": identity.platform_uid, "platform_name": identity.platform_name,
            "metadata": identity.metadata, "linked_at": identity.linked_at,
        }
        self._db.collection("users").document(identity.user_id) \
            .collection("platform_identities").document(identity.id).set(doc)
        return identity

    def get_user_by_platform(self, platform: str, platform_uid: str) -> Optional[UserDTO]:
        # Search across all users' platform_identities (use collection group query)
        from google.cloud.firestore_v1.base_query import FieldFilter
        docs = self._db.collection_group("platform_identities") \
            .where(filter=FieldFilter("platform", "==", platform)) \
            .where(filter=FieldFilter("platform_uid", "==", platform_uid)) \
            .limit(1).stream()
        for doc in docs:
            user_id = doc.to_dict().get("user_id")
            if user_id:
                return self.get_user_by_id(user_id)
        return None

    def get_platform_identities(self, user_id: str) -> list[PlatformIdentityDTO]:
        docs = self._db.collection("users").document(user_id) \
            .collection("platform_identities").stream()
        return [PlatformIdentityDTO(
            id=d.id, user_id=user_id, platform=d.to_dict().get("platform", ""),
            platform_uid=d.to_dict().get("platform_uid", ""),
            platform_name=d.to_dict().get("platform_name", ""),
            metadata=d.to_dict().get("metadata", "{}"),
            linked_at=d.to_dict().get("linked_at"),
        ) for d in docs]

    # ── Conversations ──

    def create_conversation(self, conv: ConversationDTO) -> ConversationDTO:
        now = _now_iso()
        conv.created_at = conv.created_at or now
        conv.updated_at = now
        doc = {
            "user_id": conv.user_id, "title": conv.title,
            "platform": conv.platform, "is_active": conv.is_active,
            "created_at": conv.created_at, "updated_at": conv.updated_at,
        }
        self._db.collection("conversations").document(conv.id).set(doc)
        return conv

    def get_conversation(self, conv_id: str) -> Optional[ConversationDTO]:
        doc = self._db.collection("conversations").document(conv_id).get()
        if not doc.exists:
            return None
        d = doc.to_dict()
        return ConversationDTO(
            id=doc.id, user_id=d.get("user_id", ""), title=d.get("title", ""),
            platform=d.get("platform", "web"), is_active=d.get("is_active", True),
            created_at=d.get("created_at"), updated_at=d.get("updated_at"),
        )

    def list_conversations(self, user_id: str, limit: int = 50) -> list[ConversationDTO]:
        docs = self._db.collection("conversations") \
            .where("user_id", "==", user_id) \
            .stream()
        conversations = [ConversationDTO(
            id=d.id, user_id=d.to_dict().get("user_id", ""),
            title=d.to_dict().get("title", ""),
            platform=d.to_dict().get("platform", "web"),
            is_active=d.to_dict().get("is_active", True),
            created_at=d.to_dict().get("created_at"),
            updated_at=d.to_dict().get("updated_at"),
        ) for d in docs]
        conversations.sort(key=lambda c: c.updated_at or c.created_at or "", reverse=True)
        return conversations[:limit]

    def update_conversation(self, conv: ConversationDTO) -> ConversationDTO:
        conv.updated_at = _now_iso()
        self._db.collection("conversations").document(conv.id).update({
            "title": conv.title, "is_active": conv.is_active, "updated_at": conv.updated_at,
        })
        return conv

    def save_evc_state(self, conv_id: str, evc_state: dict, last_turn_ts: float):
        self._db.collection("conversations").document(conv_id).update({
            "evc_state": evc_state,
            "last_turn_ts": last_turn_ts,
            "updated_at": _now_iso(),
        })

    def get_evc_state(self, conv_id: str) -> tuple[Optional[dict], Optional[float]]:
        doc = self._db.collection("conversations").document(conv_id).get()
        if not doc.exists:
            return None, None
        d = doc.to_dict()
        return d.get("evc_state"), d.get("last_turn_ts")

    # ── Messages ──

    def create_message(self, msg: MessageDTO) -> MessageDTO:
        msg.created_at = msg.created_at or _now_iso()
        doc = {
            "conversation_id": msg.conversation_id, "role": msg.role,
            "content": msg.content, "signals_s": msg.signals_s,
            "signals_d": msg.signals_d, "signals_c": msg.signals_c,
            "dominant_emotion": msg.dominant_emotion, "trust_level": msg.trust_level,
            "metadata": msg.metadata, "created_at": msg.created_at,
        }
        self._db.collection("conversations").document(msg.conversation_id) \
            .collection("messages").document(msg.id).set(doc)
        self._db.collection("conversations").document(msg.conversation_id).update({
            "updated_at": _now_iso(),
        })
        return msg

    def get_messages(self, conversation_id: str, limit: int = 100) -> list[MessageDTO]:
        docs = self._db.collection("conversations").document(conversation_id) \
            .collection("messages").order_by("created_at").limit(limit).stream()
        return [MessageDTO(
            id=d.id, conversation_id=conversation_id, role=d.to_dict().get("role", ""),
            content=d.to_dict().get("content", ""),
            signals_s=d.to_dict().get("signals_s"),
            signals_d=d.to_dict().get("signals_d"),
            signals_c=d.to_dict().get("signals_c"),
            dominant_emotion=d.to_dict().get("dominant_emotion"),
            trust_level=d.to_dict().get("trust_level"),
            metadata=d.to_dict().get("metadata", "{}"),
            created_at=d.to_dict().get("created_at"),
        ) for d in docs]

    def get_recent_messages(self, user_id: str, limit: int = 20) -> list[MessageDTO]:
        convs = self.list_conversations(user_id, limit=5)
        all_msgs: list[MessageDTO] = []
        for c in convs:
            msgs = self.get_messages(c.id, limit=limit)
            all_msgs.extend(msgs)
        all_msgs.sort(key=lambda m: m.created_at or "", reverse=True)
        return all_msgs[:limit]

    # ── User Facts ──

    def upsert_fact(self, fact: UserFactDTO) -> UserFactDTO:
        now = _now_iso()
        fact.last_confirmed = now
        ref = self._db.collection("users").document(fact.user_id).collection("facts")
        existing = ref.where("category", "==", fact.category) \
            .where("key", "==", fact.key).limit(1).stream()
        found = None
        for d in existing:
            found = d
            break
        if found:
            old = found.to_dict()
            ref.document(found.id).update({
                "value": fact.value, "confidence": fact.confidence,
                "source": fact.source, "last_confirmed": now,
                "mention_count": old.get("mention_count", 1) + 1,
                "is_active": fact.is_active,
            })
            fact.id = found.id
            fact.mention_count = old.get("mention_count", 1) + 1
        else:
            fact.first_mentioned = fact.first_mentioned or now
            ref.document(fact.id).set({
                "user_id": fact.user_id, "category": fact.category,
                "key": fact.key, "value": fact.value,
                "confidence": fact.confidence, "source": fact.source,
                "first_mentioned": fact.first_mentioned, "last_confirmed": now,
                "mention_count": 1, "is_active": True,
            })
        return fact

    def get_facts(self, user_id: str, category: Optional[str] = None) -> list[UserFactDTO]:
        ref = self._db.collection("users").document(user_id).collection("facts") \
            .where("is_active", "==", True)
        if category:
            ref = ref.where("category", "==", category)
        docs = ref.stream()
        return [UserFactDTO(
            id=d.id, user_id=user_id, category=d.to_dict().get("category", "general"),
            key=d.to_dict().get("key", ""), value=d.to_dict().get("value", ""),
            confidence=d.to_dict().get("confidence", 1.0),
            source=d.to_dict().get("source", "conversation"),
            first_mentioned=d.to_dict().get("first_mentioned"),
            last_confirmed=d.to_dict().get("last_confirmed"),
            mention_count=d.to_dict().get("mention_count", 1),
            is_active=d.to_dict().get("is_active", True),
        ) for d in docs]

    def delete_fact(self, fact_id: str) -> bool:
        # Need to find which user owns this fact — simplified approach
        # In practice, pass user_id as well
        return False  # Placeholder — implement with user context

    # ── User Preferences ──

    def set_preference(self, pref: UserPreferenceDTO) -> UserPreferenceDTO:
        pref.updated_at = _now_iso()
        self._db.collection("users").document(pref.user_id) \
            .collection("preferences").document(pref.pref_key).set({
                "pref_value": pref.pref_value, "updated_at": pref.updated_at,
            })
        return pref

    def get_preferences(self, user_id: str) -> list[UserPreferenceDTO]:
        docs = self._db.collection("users").document(user_id) \
            .collection("preferences").stream()
        return [UserPreferenceDTO(
            user_id=user_id, pref_key=d.id,
            pref_value=d.to_dict().get("pref_value", ""),
            updated_at=d.to_dict().get("updated_at"),
        ) for d in docs]

    def get_preference(self, user_id: str, pref_key: str) -> Optional[UserPreferenceDTO]:
        doc = self._db.collection("users").document(user_id) \
            .collection("preferences").document(pref_key).get()
        if not doc.exists:
            return None
        return UserPreferenceDTO(
            user_id=user_id, pref_key=pref_key,
            pref_value=doc.to_dict().get("pref_value", ""),
            updated_at=doc.to_dict().get("updated_at"),
        )

    # ── Conversation Summaries ──

    def create_summary(self, summary: ConversationSummaryDTO) -> ConversationSummaryDTO:
        summary.created_at = summary.created_at or _now_iso()
        self._db.collection("users").document(summary.user_id) \
            .collection("summaries").document(summary.id).set({
                "conversation_id": summary.conversation_id,
                "summary": summary.summary, "key_topics": summary.key_topics,
                "emotional_arc": summary.emotional_arc, "created_at": summary.created_at,
            })
        return summary

    def get_summaries(self, user_id: str, limit: int = 20) -> list[ConversationSummaryDTO]:
        docs = self._db.collection("users").document(user_id) \
            .collection("summaries").order_by("created_at", direction="DESCENDING") \
            .limit(limit).stream()
        return [ConversationSummaryDTO(
            id=d.id, conversation_id=d.to_dict().get("conversation_id", ""),
            user_id=user_id, summary=d.to_dict().get("summary", ""),
            key_topics=d.to_dict().get("key_topics", "[]"),
            emotional_arc=d.to_dict().get("emotional_arc", "{}"),
            created_at=d.to_dict().get("created_at"),
        ) for d in docs]

    # ── EVC Snapshots ──

    def save_evc_snapshot(self, snapshot: EVCSnapshotDTO) -> EVCSnapshotDTO:
        snapshot.created_at = snapshot.created_at or _now_iso()
        self._db.collection("users").document(snapshot.user_id) \
            .collection("evc_snapshots").document(snapshot.id).set({
                "conversation_id": snapshot.conversation_id, "turn": snapshot.turn,
                "hormones": snapshot.hormones, "emotions": snapshot.emotions,
                "trust": snapshot.trust, "memory_vector": snapshot.memory_vector,
                "created_at": snapshot.created_at,
            })
        return snapshot

    def get_latest_evc_snapshot(self, user_id: str) -> Optional[EVCSnapshotDTO]:
        docs = self._db.collection("users").document(user_id) \
            .collection("evc_snapshots").order_by("created_at", direction="DESCENDING") \
            .limit(1).stream()
        for d in docs:
            return EVCSnapshotDTO(
                id=d.id, user_id=user_id,
                conversation_id=d.to_dict().get("conversation_id"),
                turn=d.to_dict().get("turn", 0),
                hormones=d.to_dict().get("hormones", "{}"),
                emotions=d.to_dict().get("emotions", "{}"),
                trust=d.to_dict().get("trust", 0.5),
                memory_vector=d.to_dict().get("memory_vector", "{}"),
                created_at=d.to_dict().get("created_at"),
            )
        return None

    # ── Lifecycle ──

    def close(self) -> None:
        pass  # Firestore client doesn't need explicit close
