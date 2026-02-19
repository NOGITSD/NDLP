"""
User Emotion Tracker
====================
Tracks user's emotional signals (S, D, C, user_emotion) across turns
to build a rich emotional profile. Enables Jarvis to answer questions
like "How am I feeling?" with data-backed insights.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


# Mood thresholds
_STRESSED_D_THRESHOLD = 0.45
_HAPPY_S_THRESHOLD = 0.55
_NEUTRAL_MARGIN = 0.15

# Trend detection: compare recent vs older window
_RECENT_WINDOW = 5
_OLDER_WINDOW = 15
_TREND_THRESHOLD = 0.12  # minimum difference to declare a trend

MAX_HISTORY = 50


@dataclass
class EmotionRecord:
    """Single turn record of user emotional signals."""
    turn: int
    S: float
    D: float
    C: float
    user_emotion: str
    message_preview: str = ""


class UserEmotionTracker:
    """
    Tracks user emotional signals over time and produces
    human-readable summaries for the LLM system prompt.
    """

    def __init__(self) -> None:
        self.history: deque[EmotionRecord] = deque(maxlen=MAX_HISTORY)
        self.turn_count: int = 0

    # ── Recording ──

    def record_turn(
        self,
        S: float,
        D: float,
        C: float,
        user_emotion: str,
        message_preview: str = "",
    ) -> None:
        """Record one turn of user emotional data."""
        self.turn_count += 1
        self.history.append(EmotionRecord(
            turn=self.turn_count,
            S=round(S, 4),
            D=round(D, 4),
            C=round(C, 4),
            user_emotion=user_emotion,
            message_preview=message_preview[:60],
        ))

    # ── Analysis ──

    def _avg(self, records: list[EmotionRecord], key: str) -> float:
        if not records:
            return 0.5
        return sum(getattr(r, key) for r in records) / len(records)

    def get_current_mood(self) -> str:
        """Get a Thai-friendly label for the user's current mood."""
        if len(self.history) == 0:
            return "ยังไม่มีข้อมูล"

        recent = list(self.history)[-_RECENT_WINDOW:]
        avg_s = self._avg(recent, "S")
        avg_d = self._avg(recent, "D")

        # Determine mood from S/D balance
        if avg_d >= _STRESSED_D_THRESHOLD and avg_d > avg_s:
            if avg_d >= 0.65:
                return "เครียดมาก / ไม่สบายใจ"
            return "ค่อนข้างเครียด / กังวล"
        elif avg_s >= _HAPPY_S_THRESHOLD and avg_s > avg_d:
            if avg_s >= 0.7:
                return "มีความสุขมาก / สดใส"
            return "ค่อนข้างมีความสุข / สบายใจ"
        elif abs(avg_s - avg_d) < _NEUTRAL_MARGIN:
            return "ปกติ / เฉยๆ"
        elif avg_s > avg_d:
            return "ค่อนข้างสบายใจ"
        else:
            return "อารมณ์ไม่ค่อยดี"

    def get_trend(self) -> str:
        """Detect emotional trend: improving, worsening, or stable."""
        if len(self.history) < _RECENT_WINDOW + 2:
            return "ยังไม่มีข้อมูลเพียงพอ"

        all_records = list(self.history)
        recent = all_records[-_RECENT_WINDOW:]
        older = all_records[-_OLDER_WINDOW:-_RECENT_WINDOW] if len(all_records) > _RECENT_WINDOW else all_records[:_RECENT_WINDOW]

        if not older:
            return "ยังไม่มีข้อมูลเพียงพอ"

        recent_positivity = self._avg(recent, "S") - self._avg(recent, "D")
        older_positivity = self._avg(older, "S") - self._avg(older, "D")
        diff = recent_positivity - older_positivity

        if diff > _TREND_THRESHOLD:
            return "อารมณ์ดีขึ้นเรื่อยๆ (improving)"
        elif diff < -_TREND_THRESHOLD:
            return "อารมณ์แย่ลง / เครียดมากขึ้น (worsening)"
        else:
            return "อารมณ์คงที่ (stable)"

    def get_recent_emotion_labels(self, n: int = 5) -> list[str]:
        """Get the last N user_emotion labels."""
        return [r.user_emotion for r in list(self.history)[-n:]]

    def get_emotion_stats(self) -> dict[str, float]:
        """Get average S, D, C over the session."""
        if not self.history:
            return {"avg_S": 0.5, "avg_D": 0.2, "avg_C": 1.0, "turns": 0}
        records = list(self.history)
        return {
            "avg_S": round(self._avg(records, "S"), 3),
            "avg_D": round(self._avg(records, "D"), 3),
            "avg_C": round(self._avg(records, "C"), 3),
            "turns": len(records),
        }

    # ── Prompt Building ──

    def build_user_emotion_summary(self) -> str:
        """
        Build a rich summary of user's emotional state for injection
        into the LLM system prompt.

        Returns empty string if no data yet.
        """
        if not self.history:
            return ""

        mood = self.get_current_mood()
        trend = self.get_trend()
        recent_labels = self.get_recent_emotion_labels(5)
        stats = self.get_emotion_stats()

        lines = [
            f"User's current mood: {mood}",
            f"Emotional trend: {trend}",
            f"Recent emotions (last {len(recent_labels)} turns): {' → '.join(recent_labels)}",
            f"Session stats ({stats['turns']} turns): avg positivity={stats['avg_S']:.2f}, avg negativity={stats['avg_D']:.2f}",
        ]

        # Add specific guidance
        if stats["avg_D"] >= 0.5:
            lines.append(
                "⚠ User appears significantly stressed. Be extra gentle and supportive."
            )
        elif stats["avg_S"] >= 0.65:
            lines.append(
                "✨ User is in a great mood! Match their positive energy."
            )

        lines.append(
            "If user asks how they feel, use the above data to give an empathetic, personalized answer."
        )

        return "\n".join(lines)

    # ── Serialization ──

    def get_state(self) -> dict[str, Any]:
        """Get serializable state for persistence."""
        return {
            "turn_count": self.turn_count,
            "history": [
                {
                    "turn": r.turn,
                    "S": r.S,
                    "D": r.D,
                    "C": r.C,
                    "user_emotion": r.user_emotion,
                    "message_preview": r.message_preview,
                }
                for r in self.history
            ],
        }

    def load_state(self, state: dict[str, Any]) -> None:
        """Restore from a previously saved state."""
        self.turn_count = state.get("turn_count", 0)
        self.history.clear()
        for entry in state.get("history", []):
            self.history.append(EmotionRecord(
                turn=entry["turn"],
                S=entry["S"],
                D=entry["D"],
                C=entry["C"],
                user_emotion=entry["user_emotion"],
                message_preview=entry.get("message_preview", ""),
            ))
