"""Groq wrapper for analyzer + chat generation.

Phase 1 note:
- Works in mock mode when GROQ_API_KEY is missing.
- Replace heuristics with stricter JSON parsing/retries in Phase 2.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from pathlib import Path

from dotenv import load_dotenv

from .prompts import ANALYZER_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT_TEMPLATE, FACT_EXTRACTOR_PROMPT

# Ensure .env is loaded from the backend directory
_BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(_BACKEND_DIR / ".env")

try:
    from groq import Groq
except Exception:  # pragma: no cover
    Groq = None  # type: ignore


@dataclass
class AnalyzerResult:
    S: float
    D: float
    C: float
    user_emotion: str


class GroqBridge:
    def __init__(self) -> None:
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.analyzer_model = os.getenv("GROQ_ANALYZER_MODEL", "llama-3.1-8b-instant")
        self.chat_model = os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")
        self.client = Groq(api_key=self.api_key) if self.api_key and Groq is not None else None

    def analyze_message(self, message: str) -> AnalyzerResult:
        if not self.client:
            # Simple fallback heuristics for Phase 1 setup
            lower = message.lower()
            negative = any(k in lower for k in ["เหนื่อย", "แย่", "เศร้า", "โกรธ", "bad", "sad", "angry"])
            return AnalyzerResult(
                S=0.2 if negative else 0.6,
                D=0.6 if negative else 0.1,
                C=1.1 if negative else 0.9,
                user_emotion="negative" if negative else "neutral-positive",
            )

        completion = self.client.chat.completions.create(
            model=self.analyzer_model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": ANALYZER_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            response_format={"type": "json_object"},
        )

        content = completion.choices[0].message.content or "{}"
        import json

        parsed: dict[str, Any] = json.loads(content)
        return AnalyzerResult(
            S=float(parsed.get("S", 0.5)),
            D=float(parsed.get("D", 0.2)),
            C=float(parsed.get("C", 1.0)),
            user_emotion=str(parsed.get("user_emotion", "neutral")),
        )

    def generate_reply(
        self,
        user_message: str,
        bot_state: dict[str, Any],
        user_emotion: str,
        *,
        memory_context: str = "",
        long_term_memory: str = "",
        skill_context: str = "",
    ) -> str:
        if not self.client:
            return "รับทราบครับ เดี๋ยวฉันช่วยคุณต่อจากบริบทเดิมให้นะ"

        system_prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(
            dominant_emotion=bot_state.get("dominant_emotion", "Neutral"),
            emotion_blend=bot_state.get("emotion_blend", "N/A"),
            trust=float(bot_state.get("trust", 0.5)),
            user_emotion=user_emotion,
        )

        # Inject long-term memory (user profile)
        if long_term_memory:
            system_prompt += f"\n\n[USER PROFILE]\n{long_term_memory[:1500]}"

        # Inject relevant memory search results
        if memory_context:
            system_prompt += f"\n\n{memory_context[:2000]}"

        # Inject matched skill instructions
        if skill_context:
            system_prompt += f"\n\n{skill_context[:1000]}"

        completion = self.client.chat.completions.create(
            model=self.chat_model,
            temperature=0.6,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return completion.choices[0].message.content or ""

    def extract_facts(self, user_message: str) -> list[dict]:
        """Extract personal facts from user message using LLM."""
        if not self.client:
            return []
        try:
            import json
            completion = self.client.chat.completions.create(
                model=self.analyzer_model,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": FACT_EXTRACTOR_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
            )
            content = completion.choices[0].message.content or "{}"
            parsed = json.loads(content)
            facts = parsed.get("facts", [])
            return [f for f in facts if isinstance(f, dict) and "key" in f and "value" in f]
        except Exception:
            return []
