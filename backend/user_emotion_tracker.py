"""
User Emotion Tracker (with real EVC Engine)
============================================
Uses a dedicated EVCEngine instance to model the user's emotional state
with real hormone dynamics (half-life decay, homeostasis, personality
sensitivity). This gives accurate hormone/emotion readings instead of
simple S/D signal mapping.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from evc_core import EVCEngine
from config import HORMONE_NAMES, EMOTION_NAMES

# Trend detection: compare recent vs older window
_RECENT_WINDOW = 5
_OLDER_WINDOW = 15
_TREND_THRESHOLD = 0.12

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
    Tracks user emotional signals using a real EVCEngine instance.
    Produces rich hormone/emotion summaries for the LLM prompt.
    """

    def __init__(self) -> None:
        self.history: deque[EmotionRecord] = deque(maxlen=MAX_HISTORY)
        self.turn_count: int = 0
        # Dedicated EVC engine for the USER's emotional state
        self.engine = EVCEngine(name="User")
        self._last_turn_result: dict = {}

    # ── Recording ──

    def record_turn(
        self,
        S: float,
        D: float,
        C: float,
        user_emotion: str,
        delta_t: float = 1.0,
        message_preview: str = "",
    ) -> dict:
        """
        Record one turn of user emotional data and process through EVC engine.

        Returns the EVC engine turn result with full hormone/emotion data.
        """
        self.turn_count += 1
        self.history.append(EmotionRecord(
            turn=self.turn_count,
            S=round(S, 4),
            D=round(D, 4),
            C=round(C, 4),
            user_emotion=user_emotion,
            message_preview=message_preview[:60],
        ))

        # Process through real EVC engine
        self._last_turn_result = self.engine.process_turn(
            S=S, D=D, C=C,
            delta_t=delta_t,
            message=message_preview[:60],
        )
        return self._last_turn_result

    # ── Analysis ──

    def _avg(self, records: list[EmotionRecord], key: str) -> float:
        if not records:
            return 0.5
        return sum(getattr(r, key) for r in records) / len(records)

    def get_current_mood(self) -> str:
        """Get a Thai-friendly label for the user's current mood."""
        if not self._last_turn_result:
            return "ยังไม่มีข้อมูล"

        dominant = self._last_turn_result.get("dominant_emotion", "Neutral")
        score = self._last_turn_result.get("dominant_score", 0)

        mood_map = {
            "Joy": "มีความสุข / สดใส",
            "Serenity": "สงบ / สบายใจ",
            "Love": "รู้สึกอบอุ่น / ผูกพัน",
            "Excitement": "ตื่นเต้น / กระตือรือร้น",
            "Sadness": "เศร้า / หดหู่",
            "Fear": "กลัว / กังวล",
            "Anger": "หงุดหงิด / โกรธ",
            "Surprise": "ประหลาดใจ",
        }
        base = mood_map.get(dominant, "ปกติ")
        if score >= 0.4:
            return f"{base} (ค่อนข้างมาก)"
        return base

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
        Build a rich summary of user's emotional state using real EVC data.
        Returns empty string if no data yet.
        """
        if not self._last_turn_result:
            return ""

        tr = self._last_turn_result
        mood = self.get_current_mood()
        trend = self.get_trend()
        recent_labels = self.get_recent_emotion_labels(5)

        # Real hormone levels from EVC engine
        hormones = tr.get("hormones", {})
        emotions = tr.get("emotions", {})
        dominant = tr.get("dominant_emotion", "Neutral")
        dominant_score = tr.get("dominant_score", 0)
        emotion_blend = tr.get("emotion_blend", "N/A")
        trust = tr.get("trust", 0.5)

        lines = [
            "=== USER EMOTIONAL ANALYSIS (real EVC Engine data) ===",
            f"Overall mood: {mood}",
            f"Trend: {trend}",
            f"Dominant emotion: {dominant} ({dominant_score:.0%})",
            f"Emotion blend: {emotion_blend}",
            "",
            "--- User's Hormone Levels (real EVC calculation) ---",
        ]

        # Add real hormone values
        for name in HORMONE_NAMES:
            val = hormones.get(name, 0.0)
            level_label = self._hormone_label(val)
            lines.append(f"  {name}: {val:.0%} ({level_label})")

        lines.append("")
        lines.append("--- User's Emotion Scores ---")
        for name in EMOTION_NAMES:
            val = emotions.get(name, 0.0)
            if val > 0.01:  # only show non-zero emotions
                lines.append(f"  {name}: {val:.0%}")

        # Recent signal history
        lines.append("")
        lines.append("--- Recent Signal History ---")
        lines.append(f"  Recent emotions: {' → '.join(recent_labels)}")

        recent_records = list(self.history)[-3:]
        for r in recent_records:
            lines.append(
                f"  Turn {r.turn}: S={r.S:.2f} D={r.D:.2f} C={r.C:.2f} → {r.user_emotion}"
            )

        # Guidance
        cortisol = hormones.get("Cortisol", 0.0)
        dopamine = hormones.get("Dopamine", 0.0)
        lines.append("")
        if cortisol >= 0.45:
            lines.append("⚠ User's Cortisol is elevated — they are stressed. Be supportive.")
        elif dopamine >= 0.45:
            lines.append("✨ User's Dopamine is high — they are in a good mood!")

        lines.append("")
        lines.append(
            "IMPORTANT: The hormone/emotion data above is REAL data from your EVC analysis system. "
            "When user asks about their emotional state, feelings, or hormones, "
            "reference these EXACT numbers. Do NOT say you lack data."
        )

        return "\n".join(lines)

    @staticmethod
    def _hormone_label(value: float) -> str:
        """Human-readable label for hormone level."""
        if value >= 0.6:
            return "สูง"
        elif value >= 0.4:
            return "ปานกลาง-สูง"
        elif value >= 0.25:
            return "ปานกลาง"
        elif value >= 0.1:
            return "ต่ำ"
        else:
            return "ต่ำมาก"

    # ── Serialization ──

    def get_state(self) -> dict[str, Any]:
        """Get serializable state for persistence."""
        return {
            "turn_count": self.turn_count,
            "engine_state": self.engine.get_full_state(),
            "last_turn_result": self._serialize_turn_result(self._last_turn_result),
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

        # Restore EVC engine state
        engine_state = state.get("engine_state")
        if engine_state:
            self.engine.load_state(engine_state)

        # Restore last turn result
        self._last_turn_result = state.get("last_turn_result", {})

        # Restore history
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

    @staticmethod
    def _serialize_turn_result(result: dict) -> dict:
        """Make turn result JSON-serializable (convert numpy types)."""
        if not result:
            return {}
        serializable = {}
        for k, v in result.items():
            if isinstance(v, dict):
                serializable[k] = {
                    sk: float(sv) if hasattr(sv, '__float__') else sv
                    for sk, sv in v.items()
                }
            elif isinstance(v, (list, tuple)):
                serializable[k] = [
                    (float(x) if hasattr(x, '__float__') else x) for x in v
                ]
            elif hasattr(v, '__float__') and not isinstance(v, (int, float, str, bool)):
                serializable[k] = float(v)
            else:
                serializable[k] = v
        return serializable
