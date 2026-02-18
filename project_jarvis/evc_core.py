"""
EVC v2 Core Engine
==================
Main orchestrator: ties together Hormones, Emotions, Memory, and Trust
into a single pipeline per conversation turn.
"""

import numpy as np
from hormones import HormoneSystem
from emotions import EmotionMapper
from config import (
    MEMORY_BETA, TRUST_GAMMA, TRUST_LAMBDA, TRUST_INITIAL,
    H_BASELINE, HORMONE_NAMES, EMOTION_NAMES, NUM_HORMONES,
    TRUST_MIN, TRUST_MAX, TRUST_UP_EXP, TRUST_DOWN_EXP,
)


class EVCEngine:
    """
    Emotional Value Core v2 — Hormone-First Pipeline
    
    Pipeline per turn:
    1. Receive S, D, C (from LLM or manual)
    2. Calculate stimulus → update hormones (with half-life)
    3. Map hormones → emotions (W × H)
    4. Update emotional memory
    5. Update trust level
    6. Output: hormone state + emotion blend + trust
    """

    def __init__(self, personality=None, name="Jarvis"):
        """
        Args:
            personality: np.array(8) sensitivity profile, or None for default.
            name: Name of the bot (for display).
        """
        self.name = name
        self.hormones = HormoneSystem(personality=personality)
        self.emotions = EmotionMapper()
        
        # Emotional memory (vector of 8, tracks long-term hormone pattern)
        self.memory = H_BASELINE.copy()
        
        # Trust level
        self.trust = TRUST_INITIAL
        
        # Turn counter
        self.turn = 0
        
        # Full turn log
        self.turn_log = []
    
    def process_turn(self, S: float, D: float, C: float = 1.0,
                     delta_t: float = 1.0, message: str = "") -> dict:
        """
        Process one conversation turn.
        
        Args:
            S: Positive signal [0, 1]
            D: Negative signal [0, 1]
            C: Context weight [0.5, 1.5]
            delta_t: Time since last turn (in turns)
            message: The user message (for logging)
        
        Returns:
            dict with all state information
        """
        self.turn += 1
        
        # 1. Update hormones
        H = self.hormones.update(S, D, C, delta_t)
        delta_H = self.hormones.get_delta()
        
        # 2. Compute emotions from hormones
        E = self.emotions.compute(H)
        dominant_name, dominant_score = self.emotions.get_dominant()
        top3 = self.emotions.get_top_n(3)
        emotion_label = self.emotions.get_emotion_label()
        
        # 3. Update emotional memory
        self.memory = MEMORY_BETA * self.memory + (1 - MEMORY_BETA) * H
        
        # 4. Update trust (adaptive, avoids hard saturation at 0/1)
        trust_room_up = max(TRUST_MAX - self.trust, 0.0)
        trust_room_down = max(self.trust - TRUST_MIN, 0.0)
        trust_up = TRUST_GAMMA * S * (trust_room_up ** TRUST_UP_EXP)
        trust_down = TRUST_LAMBDA * D * (trust_room_down ** TRUST_DOWN_EXP)
        self.trust = np.clip(self.trust + trust_up - trust_down, TRUST_MIN, TRUST_MAX)
        
        # 5. Output intensity (trust-modulated)
        output_intensity = float(self.trust * dominant_score)
        
        # 6. Build result
        result = {
            "turn": self.turn,
            "message": message,
            "delta_t": round(float(delta_t), 4),
            "input": {"S": S, "D": D, "C": C},
            "hormones": self.hormones.get_state_dict(),
            "hormone_delta": {
                name: round(float(val), 4) 
                for name, val in zip(HORMONE_NAMES, delta_H)
            },
            "emotions": self.emotions.get_state_dict(),
            "dominant_emotion": dominant_name,
            "dominant_score": round(dominant_score, 4),
            "emotion_blend": emotion_label,
            "top3_emotions": top3,
            "memory": {
                name: round(float(val), 4)
                for name, val in zip(HORMONE_NAMES, self.memory)
            },
            "trust": round(float(self.trust), 4),
            "output_intensity": round(output_intensity, 4),
        }
        
        self.turn_log.append(result)
        return result
    
    def get_prompt_injection(self) -> str:
        """
        Generate a system prompt fragment describing current emotional state.
        This gets injected into the LLM prompt for response generation.
        """
        dominant, score = self.emotions.get_dominant()
        blend = self.emotions.get_emotion_label()
        
        return (
            f"[EVC STATE] Turn {self.turn}\n"
            f"Hormones: {self.hormones.get_state_dict()}\n"
            f"Emotion: {blend}\n"
            f"Dominant: {dominant} ({score:.2f})\n"
            f"Trust: {self.trust:.2f}\n"
            f"Respond naturally with tone matching: {dominant}"
        )
    
    def get_summary(self) -> str:
        """Get a one-line summary of current state."""
        dominant, score = self.emotions.get_dominant()
        return (
            f"[Turn {self.turn}] "
            f"{self.emotions.get_emotion_label()} | "
            f"Trust: {self.trust:.2f}"
        )
    
    def get_full_state(self) -> dict:
        """Get complete engine state (for save/load)."""
        return {
            "turn": self.turn,
            "hormones": self.hormones.H.tolist(),
            "memory": self.memory.tolist(),
            "trust": float(self.trust),
            "name": self.name,
        }
    
    def load_state(self, state: dict):
        """Load a previously saved state."""
        self.turn = state["turn"]
        self.hormones.H = np.array(state["hormones"])
        self.hormones.H_prev = self.hormones.H.copy()
        self.memory = np.array(state["memory"])
        self.trust = state["trust"]
        self.name = state.get("name", self.name)
    
    def reset(self):
        """Reset engine to initial state."""
        self.hormones.reset()
        self.emotions.reset()
        self.memory = H_BASELINE.copy()
        self.trust = TRUST_INITIAL
        self.turn = 0
        self.turn_log = []
