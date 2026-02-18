"""
User Memory Service — makes the bot "know" the user.
Extracts facts from conversation, stores preferences, builds context for LLM.
"""

from __future__ import annotations

import json
import uuid
from typing import Optional

from .db.base_repository import (
    BaseRepository, UserFactDTO, UserPreferenceDTO,
    ConversationSummaryDTO, EVCSnapshotDTO,
)


# Categories for user facts
FACT_CATEGORIES = {
    "personal": ["name", "nickname", "age", "birthday", "gender", "location", "hometown"],
    "preference": ["language", "food", "music", "color", "hobby", "style"],
    "work": ["job", "company", "school", "major", "project", "schedule"],
    "relationship": ["family", "partner", "friend", "pet"],
    "general": [],  # catch-all
}


class UserMemoryService:
    """
    Manages what the bot knows about a specific user.
    Provides context injection for LLM prompts.
    """

    def __init__(self, repo: BaseRepository, user_id: str):
        self.repo = repo
        self.user_id = user_id

    # ── Fact Management ───────────────────────────────────────────────

    def learn_fact(self, key: str, value: str,
                   category: str = "general",
                   confidence: float = 0.8,
                   source: str = "conversation") -> UserFactDTO:
        """Store or update a fact about the user."""
        fact = UserFactDTO(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            category=category,
            key=key,
            value=value,
            confidence=confidence,
            source=source,
        )
        return self.repo.upsert_fact(fact)

    def get_all_facts(self) -> list[UserFactDTO]:
        return self.repo.get_facts(self.user_id)

    def get_facts_by_category(self, category: str) -> list[UserFactDTO]:
        return self.repo.get_facts(self.user_id, category=category)

    def forget_fact(self, fact_id: str) -> bool:
        return self.repo.delete_fact(fact_id)

    # ── Preference Management ─────────────────────────────────────────

    def set_preference(self, key: str, value: str) -> UserPreferenceDTO:
        pref = UserPreferenceDTO(
            user_id=self.user_id,
            pref_key=key,
            pref_value=value,
        )
        return self.repo.set_preference(pref)

    def get_preference(self, key: str) -> Optional[str]:
        pref = self.repo.get_preference(self.user_id, key)
        return pref.pref_value if pref else None

    def get_all_preferences(self) -> dict[str, str]:
        prefs = self.repo.get_preferences(self.user_id)
        return {p.pref_key: p.pref_value for p in prefs}

    # ── EVC State Persistence ─────────────────────────────────────────

    def save_evc_state(self, conversation_id: str, turn: int,
                       hormones: dict, emotions: dict,
                       trust: float, memory_vector: dict) -> EVCSnapshotDTO:
        snapshot = EVCSnapshotDTO(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            conversation_id=conversation_id,
            turn=turn,
            hormones=json.dumps(hormones),
            emotions=json.dumps(emotions),
            trust=trust,
            memory_vector=json.dumps(memory_vector),
        )
        return self.repo.save_evc_snapshot(snapshot)

    def load_evc_state(self) -> Optional[dict]:
        snapshot = self.repo.get_latest_evc_snapshot(self.user_id)
        if not snapshot:
            return None
        return {
            "turn": snapshot.turn,
            "hormones": json.loads(snapshot.hormones),
            "emotions": json.loads(snapshot.emotions),
            "trust": snapshot.trust,
            "memory_vector": json.loads(snapshot.memory_vector),
        }

    # ── Conversation Summaries ────────────────────────────────────────

    def save_summary(self, conversation_id: str, summary: str,
                     key_topics: list[str] = None,
                     emotional_arc: dict = None) -> ConversationSummaryDTO:
        s = ConversationSummaryDTO(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            user_id=self.user_id,
            summary=summary,
            key_topics=json.dumps(key_topics or []),
            emotional_arc=json.dumps(emotional_arc or {}),
        )
        return self.repo.create_summary(s)

    def get_recent_summaries(self, limit: int = 10) -> list[dict]:
        summaries = self.repo.get_summaries(self.user_id, limit=limit)
        return [{
            "id": s.id,
            "conversation_id": s.conversation_id,
            "summary": s.summary,
            "key_topics": json.loads(s.key_topics) if s.key_topics else [],
            "emotional_arc": json.loads(s.emotional_arc) if s.emotional_arc else {},
            "created_at": s.created_at,
        } for s in summaries]

    # ── Context Builder (for LLM prompt injection) ────────────────────

    def build_user_profile_context(self) -> str:
        """
        Build a concise user profile string for LLM context.
        This is what makes the bot "know" the user.
        """
        facts = self.get_all_facts()
        prefs = self.get_all_preferences()
        summaries = self.get_recent_summaries(limit=5)

        parts = ["[USER PROFILE]"]

        # Group facts by category
        if facts:
            by_cat: dict[str, list[UserFactDTO]] = {}
            for f in facts:
                by_cat.setdefault(f.category, []).append(f)

            for cat, cat_facts in by_cat.items():
                items = ", ".join(f"{f.key}: {f.value}" for f in cat_facts[:10])
                parts.append(f"  {cat.title()}: {items}")

        # Preferences
        if prefs:
            pref_str = ", ".join(f"{k}: {v}" for k, v in list(prefs.items())[:10])
            parts.append(f"  Preferences: {pref_str}")

        # Recent conversation summaries
        if summaries:
            parts.append("  Recent conversations:")
            for s in summaries[:3]:
                topics = ", ".join(s.get("key_topics", [])[:5])
                parts.append(f"    - {s['summary'][:100]} (topics: {topics})")

        if len(parts) == 1:
            parts.append("  (New user — no information yet)")

        return "\n".join(parts)

    def build_memory_context_for_chat(self) -> str:
        """
        Shorter version for per-turn injection.
        Focuses on key facts + preferences.
        """
        facts = self.get_all_facts()
        if not facts:
            return ""

        high_conf = [f for f in facts if f.confidence >= 0.6][:15]
        if not high_conf:
            return ""

        lines = ["[KNOWN ABOUT USER]"]
        for f in high_conf:
            lines.append(f"- {f.key}: {f.value} ({f.category})")
        return "\n".join(lines)
