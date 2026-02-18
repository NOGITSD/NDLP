"""
EVC v2 Emotion Module
=====================
Maps 8 hormone levels to 8 emotion scores via W matrix.
Handles normalization, blending, and dominant emotion detection.
"""

import numpy as np
from config import W_MATRIX, EMOTION_NAMES, NUM_EMOTIONS


class EmotionMapper:
    """
    Converts hormone vector H[8] to emotion vector E[8]
    using the W matrix (8×8 linear transformation).
    """

    def __init__(self):
        self.W = W_MATRIX.copy()
        self.emotions_raw = np.zeros(NUM_EMOTIONS)
        self.emotions_normalized = np.zeros(NUM_EMOTIONS)
        self.history = []
    
    def compute(self, H: np.ndarray) -> np.ndarray:
        """
        Compute emotion scores from hormone levels.
        
        Steps:
        1. E_raw = W × H (matrix multiply)
        2. ReLU: E = max(0, E_raw)
        3. Normalize: E = E / sum(E) so they sum to 1
        
        Args:
            H: Hormone vector, np.array of shape (8,)
        
        Returns:
            emotions_normalized: np.array of shape (8,), sums to 1.0
        """
        # 1. Matrix multiply
        self.emotions_raw = self.W @ H
        
        # 2. ReLU — no negative emotions
        self.emotions_raw = np.maximum(0.0, self.emotions_raw)
        
        # 3. Normalize to probability distribution
        total = self.emotions_raw.sum()
        if total > 0:
            self.emotions_normalized = self.emotions_raw / total
        else:
            # Uniform if all zero (shouldn't happen)
            self.emotions_normalized = np.ones(NUM_EMOTIONS) / NUM_EMOTIONS
        
        # Record history
        self.history.append(self.emotions_normalized.copy())
        
        return self.emotions_normalized
    
    def get_dominant(self) -> tuple:
        """
        Get the dominant emotion.
        
        Returns:
            (emotion_name, score)
        """
        idx = np.argmax(self.emotions_normalized)
        return EMOTION_NAMES[idx], float(self.emotions_normalized[idx])
    
    def get_top_n(self, n: int = 3) -> list:
        """
        Get top N emotions with scores.
        
        Returns:
            List of (emotion_name, score) sorted by score descending.
        """
        indices = np.argsort(self.emotions_normalized)[::-1][:n]
        return [
            (EMOTION_NAMES[i], round(float(self.emotions_normalized[i]), 4))
            for i in indices
        ]
    
    def get_state_dict(self) -> dict:
        """
        Get current emotion state as readable dictionary.
        """
        return {
            name: round(float(val), 4)
            for name, val in zip(EMOTION_NAMES, self.emotions_normalized)
        }
    
    def get_emotion_label(self) -> str:
        """
        Get a human-readable emotion blend label.
        Example: "Joy(0.35) + Love(0.25) + Serenity(0.20)"
        """
        top3 = self.get_top_n(3)
        parts = [f"{name}({score:.2f})" for name, score in top3]
        return " + ".join(parts)
    
    def reset(self):
        """Reset emotion state."""
        self.emotions_raw = np.zeros(NUM_EMOTIONS)
        self.emotions_normalized = np.zeros(NUM_EMOTIONS)
        self.history = []
    
    def get_history_array(self) -> np.ndarray:
        """
        Get full emotion history as numpy array.
        
        Returns:
            np.ndarray of shape (num_turns, 8)
        """
        return np.array(self.history)
