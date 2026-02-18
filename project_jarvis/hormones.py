"""
EVC v2 Hormone Module
=====================
Handles stimulus calculation and hormone dynamics with biological half-life.
"""

import numpy as np
from config import (
    NUM_HORMONES, H_BASELINE, HALF_LIFE_TURNS,
    P_POS, P_NEG, RECOVERY_RATE, PERSONALITY_DEFAULT,
    H_INTERACT, INTERACTION_STRENGTH, NEGATIVITY_BIAS,
    HALF_LIFE_MIN_FACTOR, HALF_LIFE_MAX_FACTOR,
    HALF_LIFE_STRESS_SENS, HALF_LIFE_ACTIVATION_SENS,
    STIMULUS_GAIN, SOFT_CLAMP_SHARPNESS,
)


class HormoneSystem:
    """
    Manages 8 hormone levels with:
    - Stimulus impact from positive/negative signals
    - Exponential decay based on real half-life
    - Homeostasis recovery toward baseline
    - Personality-based sensitivity
    """

    def __init__(self, personality=None):
        """
        Initialize hormone system.
        
        Args:
            personality: np.array of shape (8,) — sensitivity per hormone.
                         If None, uses default balanced personality.
        """
        # Current hormone levels (start at baseline)
        self.H = H_BASELINE.copy()
        
        # Previous hormone levels (for delta calculation)
        self.H_prev = H_BASELINE.copy()
        
        # Personality (sensitivity per hormone)
        self.K = personality if personality is not None else PERSONALITY_DEFAULT.copy()
        
        # History for tracking
        self.history = [self.H.copy()]
    
    def calculate_stimulus(self, S: float, D: float, C: float) -> np.ndarray:
        """
        Calculate how S (positive) and D (negative) signals
        affect each hormone through stimulus profile matrices.
        
        Formula: Stimulus[i] = P_pos[i] * S * C  -  P_neg[i] * D_eff * C
        where D_eff = D * NEGATIVITY_BIAS (humans respond ~2.5x stronger to negative)
        
        Args:
            S: Positive signal [0, 1]
            D: Negative signal [0, 1]
            C: Context weight [0.5, 1.5]
        
        Returns:
            stimulus: np.array of shape (8,)
        """
        D_eff = D * NEGATIVITY_BIAS
        stimulus = P_POS * S * C - P_NEG * D_eff * C
        return stimulus

    def _compute_decay_factor(self, D: float, C: float, delta_t: float) -> np.ndarray:
        """
        Compute per-hormone decay factor using dynamic half-life.

        Half-life varies with:
        - stress level (D * C)
        - current activation distance from baseline
        """
        stress_level = float(np.clip(D * C, 0.0, 1.5))
        activation = np.abs(self.H - H_BASELINE)

        half_life_factor = (
            1.0
            + HALF_LIFE_STRESS_SENS * stress_level
            + HALF_LIFE_ACTIVATION_SENS * activation
        )
        half_life_factor = np.clip(
            half_life_factor,
            HALF_LIFE_MIN_FACTOR,
            HALF_LIFE_MAX_FACTOR,
        )

        effective_half_life = HALF_LIFE_TURNS * half_life_factor
        dynamic_lambda = np.log(2.0) / np.maximum(effective_half_life, 1e-6)
        return np.exp(-dynamic_lambda * delta_t)

    def _soft_clip01(self, x: np.ndarray) -> np.ndarray:
        """Smoothly bound values to [0,1] to reduce hard clipping artifacts."""
        z = (x - 0.5) * SOFT_CLAMP_SHARPNESS
        return 1.0 / (1.0 + np.exp(-z))
    
    def update(self, S: float, D: float, C: float, delta_t: float = 1.0) -> np.ndarray:
        """
        Update all hormone levels for one turn.
        
        Pipeline:
        1. Calculate stimulus from S, D, C
        2. Apply half-life decay: H *= e^(-λ * Δt)
        3. Add stimulus impact (scaled by personality K)
        4. Apply homeostasis recovery toward baseline
        5. Clamp to [0, 1]
        
        Args:
            S: Positive signal [0, 1]
            D: Negative signal [0, 1]
            C: Context weight [0.5, 1.5]
            delta_t: Time elapsed (in turns). Default 1.0 for normal chat.
                     Can be > 1 if user was away (hormones decay more).
        
        Returns:
            H: Updated hormone levels, np.array of shape (8,)
        """
        # Save previous
        self.H_prev = self.H.copy()
        
        # 1. Stimulus (with negativity bias baked in)
        stimulus = self.calculate_stimulus(S, D, C)
        
        # 2. Dynamic half-life decay
        decay_factor = self._compute_decay_factor(D=D, C=C, delta_t=delta_t)
        
        # 3. Core dynamics: decay + stimulus + homeostasis
        self.H = (
            self.H * decay_factor                             # half-life decay
            + STIMULUS_GAIN * (self.K * stimulus)            # stimulus impact (scaled)
            + RECOVERY_RATE * (H_BASELINE - self.H)          # homeostasis pull
        )
        
        # 4. Cross-interaction between hormones
        #    e.g. Cortisol suppresses Serotonin, GABA inhibits Adrenaline
        interaction_delta = INTERACTION_STRENGTH * (H_INTERACT @ self.H)
        self.H = self.H + interaction_delta
        
        # 5. Soft clamp to [0, 1]
        self.H = self._soft_clip01(self.H)
        
        # Record history
        self.history.append(self.H.copy())
        
        return self.H
    
    def get_delta(self) -> np.ndarray:
        """
        Get hormone change from last turn.
        
        Returns:
            delta_H: np.array of shape (8,)
        """
        return self.H - self.H_prev
    
    def get_state_dict(self) -> dict:
        """
        Get current hormone state as a readable dictionary.
        """
        from config import HORMONE_NAMES
        return {
            name: round(float(val), 4)
            for name, val in zip(HORMONE_NAMES, self.H)
        }
    
    def reset(self):
        """Reset hormones to baseline."""
        self.H = H_BASELINE.copy()
        self.H_prev = H_BASELINE.copy()
        self.history = [self.H.copy()]
    
    def get_history_array(self) -> np.ndarray:
        """
        Get full history as numpy array.
        
        Returns:
            np.ndarray of shape (num_turns+1, 8)
        """
        return np.array(self.history)
