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

        # Build recent turn-by-turn signal data
        recent_records = list(self.history)[-5:]

        lines = [
            "=== USER EMOTIONAL ANALYSIS (from EVC sensor data) ===",
            f"Overall mood: {mood}",
            f"Trend: {trend}",
            f"Recent emotion labels: {' → '.join(recent_labels)}",
            "",
            "--- Signal History (last turns) ---",
        ]

        for r in recent_records:
            lines.append(
                f"  Turn {r.turn}: S(positive)={r.S:.2f} D(negative)={r.D:.2f} "
                f"C(intensity)={r.C:.2f} → {r.user_emotion}"
            )

        # Map S/D averages to estimated user hormone levels
        avg_s = stats["avg_S"]
        avg_d = stats["avg_D"]
        lines.append("")
        lines.append("--- Estimated User Hormone Levels ---")
        lines.append(f"  Dopamine (motivation/pleasure): {self._estimate_level(avg_s, 'high_positive')}")
        lines.append(f"  Serotonin (stability/happiness): {self._estimate_level(avg_s - avg_d * 0.5, 'balanced')}")
        lines.append(f"  Cortisol (stress): {self._estimate_level(avg_d, 'high_negative')}")
        lines.append(f"  Adrenaline (anxiety/alertness): {self._estimate_level(avg_d * 0.8, 'high_negative')}")
        lines.append(f"  Oxytocin (connection/trust): {self._estimate_level(avg_s * 0.7, 'high_positive')}")
        lines.append(f"  Endorphin (comfort): {self._estimate_level(avg_s * 0.6 - avg_d * 0.3, 'balanced')}")
        lines.append("")
        lines.append(f"Session averages ({stats['turns']} turns): positivity={avg_s:.2f}, negativity={avg_d:.2f}")

        # Guidance for Jarvis
        if avg_d >= 0.5:
            lines.append("⚠ User is significantly stressed. Be extra gentle and supportive.")
        elif avg_s >= 0.65:
            lines.append("✨ User is in a great mood! Match their positive energy.")

        lines.append("")
        lines.append(
            "IMPORTANT: You HAVE real analytical data about the user's emotional state above. "
            "When the user asks about their feelings, emotions, or hormone levels, "
            "reference this data directly and give specific numbers. "
            "Do NOT say you don't have data — you DO have it from your EVC analysis system."
        )

        return "\n".join(lines)

    def _estimate_level(self, value: float, mode: str) -> str:
        """Convert a 0-1 signal value to a human-readable hormone level."""
        if mode == "high_negative":
            # Higher value = more negative hormone (cortisol, adrenaline)
            if value >= 0.6:
                return f"สูง ({value:.0%}) — ค่อนข้างสูง"
            elif value >= 0.35:
                return f"ปานกลาง ({value:.0%})"
            else:
                return f"ต่ำ ({value:.0%}) — ปกติดี"
        elif mode == "high_positive":
            # Higher value = more positive hormone (dopamine, oxytocin)
            if value >= 0.6:
                return f"สูง ({value:.0%}) — ดีมาก"
            elif value >= 0.35:
                return f"ปานกลาง ({value:.0%})"
            else:
                return f"ต่ำ ({value:.0%}) — ค่อนข้างต่ำ"
        else:  # balanced
            if value >= 0.4:
                return f"ดี ({value:.0%})"
            elif value >= 0.1:
                return f"ปานกลาง ({value:.0%})"
            elif value >= -0.1:
                return f"ต่ำ ({value:.0%})"
            else:
                return f"ต่ำมาก ({value:.0%})"

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
