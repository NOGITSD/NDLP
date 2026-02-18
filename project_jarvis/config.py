"""
EVC v2 Configuration
====================
All constants, baselines, half-lives, W matrix, and personality profiles.
"""

import math
import numpy as np

# ============================================================
# HORMONE DEFINITIONS
# ============================================================

HORMONE_NAMES = [
    "Dopamine",       # 0: reward, motivation, pleasure
    "Serotonin",      # 1: calm, stability, contentment
    "Oxytocin",       # 2: bonding, trust, closeness
    "Endorphin",      # 3: comfort, pain relief, euphoria
    "Cortisol",       # 4: stress, anxiety
    "Adrenaline",     # 5: alertness, fight/flight
    "GABA",           # 6: inhibition, calm, relaxation
    "Norepinephrine", # 7: focus, alertness, vigilance
]

EMOTION_NAMES = [
    "Joy",            # 0
    "Serenity",       # 1
    "Love",           # 2
    "Excitement",     # 3
    "Sadness",        # 4
    "Fear",           # 5
    "Anger",          # 6
    "Surprise",       # 7
]

NUM_HORMONES = 8
NUM_EMOTIONS = 8

# ============================================================
# HORMONE BASELINES (homeostasis target)
# ============================================================

H_BASELINE = np.array([
    0.50,  # Dopamine
    0.60,  # Serotonin
    0.40,  # Oxytocin
    0.30,  # Endorphin
    0.30,  # Cortisol
    0.20,  # Adrenaline
    0.50,  # GABA
    0.30,  # Norepinephrine
])

# ============================================================
# HALF-LIFE (in "turns" — scaled for chat context)
# Real half-lives scaled: 1 turn ≈ 5 minutes
# ============================================================

HALF_LIFE_TURNS = np.array([
    0.4,   # Dopamine      (~2 min real → decays fast)
    6.0,   # Serotonin     (~30 min real → decays slow)
    0.8,   # Oxytocin      (~4 min real → decays fast)
    4.0,   # Endorphin     (~20 min real → medium)
    15.0,  # Cortisol      (~75 min real → very slow!)
    0.5,   # Adrenaline    (~2.5 min real → decays fast)
    6.0,   # GABA          (~30 min real → slow)
    0.5,   # Norepinephrine (~2.5 min real → decays fast)
])

# Decay constants: λ = ln(2) / half_life
DECAY_LAMBDA = np.log(2) / HALF_LIFE_TURNS

# Dynamic half-life scaling (time-varying physiology)
# Effective half-life is adjusted every turn based on stress/activation state.
HALF_LIFE_MIN_FACTOR = 0.65
HALF_LIFE_MAX_FACTOR = 2.00

# How stress signal (D*C) changes each hormone half-life.
# Positive => longer persistence under stress, negative => faster washout under stress.
HALF_LIFE_STRESS_SENS = np.array([
    -0.15,  # Dopamine
    -0.10,  # Serotonin
    -0.20,  # Oxytocin
     0.05,  # Endorphin
     0.65,  # Cortisol
     0.45,  # Adrenaline
    -0.05,  # GABA
     0.35,  # Norepinephrine
])

# How current activation level (|H - baseline|) changes each half-life.
# Helps highly activated hormones linger realistically.
HALF_LIFE_ACTIVATION_SENS = np.array([
    0.25,  # Dopamine
    0.20,  # Serotonin
    0.20,  # Oxytocin
    0.20,  # Endorphin
    0.70,  # Cortisol
    0.40,  # Adrenaline
    0.20,  # GABA
    0.35,  # Norepinephrine
])

# ============================================================
# STIMULUS PROFILE MATRICES
# How positive (S) and negative (D) signals affect each hormone
# ============================================================

# P_pos: When user sends positive signal (praise, thanks, love)
P_POS = np.array([
    0.80,  # Dopamine ↑ (reward!)
    0.50,  # Serotonin ↑ (feels good)
    0.60,  # Oxytocin ↑ (bonding)
    0.40,  # Endorphin ↑ (comfort)
   -0.30,  # Cortisol ↓ (less stress)
    0.10,  # Adrenaline ↑ slight (excitement)
    0.30,  # GABA ↑ (relaxed)
    0.10,  # Norepinephrine ↑ slight
])

# P_neg: When user sends negative signal (insult, anger, frustration)
# Positive values = hormone DECREASES when D is high
# Negative values = hormone INCREASES when D is high
P_NEG = np.array([
    0.60,  # Dopamine ↓ (less pleasure)
    0.50,  # Serotonin ↓ (less calm)
    0.40,  # Oxytocin ↓ (less trust)
    0.20,  # Endorphin ↓ slightly
   -0.80,  # Cortisol ↑↑ (MORE stress!)
   -0.60,  # Adrenaline ↑↑ (fight/flight!)
    0.40,  # GABA ↓ (less relaxed)
   -0.50,  # Norepinephrine ↑ (alert!)
])

# ============================================================
# HORMONE CROSS-INTERACTION MATRIX
# H_INTERACT[i][j] = how hormone j affects hormone i
# Applied AFTER stimulus, models real neuroendocrine feedback loops
# Positive = promotes, Negative = inhibits
#
# Key interactions (referenced from neuroscience):
# - Cortisol suppresses Serotonin production (McEwen, 2007)
# - Oxytocin suppresses Cortisol (Heinrichs et al., 2003)
# - GABA inhibits Norepinephrine & Adrenaline (Goddard, 2016)
# - Endorphin inhibits Cortisol release
# - High Cortisol suppresses Oxytocin
# ============================================================

H_INTERACT = np.array([
    #  Dopa   Sero  Oxyto Endor Corti Adren  GABA  NorEp
    [ 0.00,  0.05,  0.03, 0.02, -0.04, 0.02, 0.00, 0.03],  # Dopamine
    [ 0.03,  0.00,  0.04, 0.03, -0.08,-0.02, 0.05,-0.02],  # Serotonin (Cortisol strongly suppresses)
    [ 0.02,  0.03,  0.00, 0.02, -0.06,-0.03, 0.03,-0.02],  # Oxytocin (Cortisol suppresses)
    [ 0.03,  0.04,  0.03, 0.00, -0.03, 0.00, 0.02, 0.00],  # Endorphin
    [-0.02, -0.03, -0.06,-0.04,  0.00, 0.04,-0.05, 0.03],  # Cortisol (Oxytocin/GABA suppress)
    [ 0.02, -0.02, -0.03, 0.00,  0.05, 0.00,-0.08, 0.05],  # Adrenaline (GABA strongly inhibits)
    [ 0.02,  0.04,  0.03, 0.03, -0.04,-0.03, 0.00,-0.03],  # GABA
    [ 0.03, -0.02, -0.02, 0.00,  0.04, 0.05,-0.06, 0.00],  # Norepinephrine (GABA inhibits)
])

INTERACTION_STRENGTH = 0.15  # Scale factor (0=off, 1=full)

# ============================================================
# NEGATIVITY BIAS
# Humans respond ~2-3x stronger to negative vs positive stimuli
# (Baumeister et al., 2001 "Bad is Stronger than Good")
# ============================================================

NEGATIVITY_BIAS = 1.5  # Reduced from 2.5 — cross-interaction already compounds negative effects

# ============================================================
# W MATRIX: Hormone → Emotion (8×8)
# W[emotion][hormone]
# Positive = hormone promotes emotion
# Negative = hormone inhibits emotion
# ============================================================

W_MATRIX = np.array([
    #  Dopa   Sero  Oxyto Endor Corti Adren  GABA  NorEp
    [ 0.35,  0.20,  0.15, 0.20, -0.15, 0.00,  0.10, 0.00],  # Joy
    [ 0.05,  0.35,  0.10, 0.15, -0.20,-0.15,  0.30,-0.10],  # Serenity
    [ 0.10,  0.15,  0.40, 0.10, -0.10,-0.05,  0.10, 0.00],  # Love
    [ 0.25, -0.05,  0.05, 0.15,  0.00, 0.30, -0.15, 0.20],  # Excitement
    [-0.20, -0.40, -0.15,-0.15,  0.45, 0.05, -0.20, 0.05],  # Sadness (Serotonin↓ = depression, Cortisol↑ = sadness)
    [-0.10, -0.15, -0.10,-0.10,  0.35, 0.25, -0.20, 0.25],  # Fear
    [-0.10, -0.20, -0.15,-0.05,  0.25, 0.20, -0.25, 0.30],  # Anger
    [ 0.10, -0.10,  0.00, 0.05,  0.10, 0.30, -0.20, 0.25],  # Surprise
])

# ============================================================
# DYNAMICS PARAMETERS
# ============================================================

ALPHA = 0.85       # Inertia (general, used as fallback)
RECOVERY_RATE = 0.10  # How fast hormones drift back to baseline
STIMULUS_GAIN = 0.60  # Global gain to reduce clipping/saturation
SOFT_CLAMP_SHARPNESS = 2.8  # lower = softer bound near [0,1]

# Personality: sensitivity per hormone (K_i)
# Default "balanced" personality
PERSONALITY_DEFAULT = np.array([
    1.0,  # Dopamine sensitivity
    1.0,  # Serotonin sensitivity
    1.0,  # Oxytocin sensitivity
    1.0,  # Endorphin sensitivity
    1.0,  # Cortisol sensitivity
    1.0,  # Adrenaline sensitivity
    1.0,  # GABA sensitivity
    1.0,  # Norepinephrine sensitivity
])

PERSONALITY_SENSITIVE = np.array([
    1.5, 0.8, 1.3, 1.0, 1.5, 1.3, 0.7, 1.2
])

PERSONALITY_CALM = np.array([
    0.8, 1.3, 1.0, 1.2, 0.6, 0.5, 1.5, 0.6
])

PERSONALITY_CHEERFUL = np.array([
    1.5, 1.2, 1.3, 1.2, 0.5, 0.5, 1.2, 0.6
])

# ============================================================
# MEMORY & TRUST
# ============================================================

MEMORY_BETA = 0.90     # Memory decay (0.85-0.95)
TRUST_GAMMA = 0.06     # Trust increase per positive signal
TRUST_LAMBDA = 0.05    # Trust decrease per negative signal
TRUST_INITIAL = 0.5    # Starting trust
TRUST_MIN = 0.05
TRUST_MAX = 0.95
TRUST_UP_EXP = 1.2     # trust-up slows near TRUST_MAX
TRUST_DOWN_EXP = 0.8   # trust-down remains effective at high trust

# ============================================================
# EVALUATION TEST MESSAGES
# Random messages for eval mode with pre-assigned S, D, C values
# ============================================================

EVAL_MESSAGES = [
    # (message, S, D, C)
    # --- Positive ---
    ("ขอบคุณมากเลย ช่วยได้เยอะ", 0.75, 0.05, 1.0),
    ("เก่งมากเลยนะ", 0.80, 0.00, 1.0),
    ("ชอบคำตอบนี้จัง", 0.70, 0.00, 1.1),
    ("ทำดีมากครับ", 0.65, 0.00, 1.0),
    ("น่ารักจัง", 0.60, 0.00, 1.2),
    ("รักเลย", 0.85, 0.00, 1.3),
    ("สุดยอดไปเลย!", 0.90, 0.00, 1.1),
    ("ขอบใจนะ", 0.55, 0.05, 1.0),
    ("ดีใจที่มีเธอ", 0.80, 0.00, 1.3),
    ("วันนี้มีความสุขมาก", 0.75, 0.00, 1.0),
    
    # --- Neutral ---
    ("สวัสดีครับ", 0.30, 0.10, 1.0),
    ("วันนี้อากาศดีนะ", 0.25, 0.05, 0.8),
    ("ช่วยเช็คตารางหน่อย", 0.15, 0.10, 1.0),
    ("โอเค", 0.20, 0.10, 0.8),
    ("อืม ได้เลย", 0.20, 0.05, 0.9),
    ("ครับ", 0.15, 0.05, 0.7),
    ("เดี๋ยวค่อยว่ากัน", 0.10, 0.15, 0.9),
    ("ไม่แน่ใจเหมือนกัน", 0.10, 0.20, 1.0),
    ("ลองดูอีกที", 0.15, 0.15, 1.0),
    ("งั้นเอาแบบนี้", 0.20, 0.10, 1.0),
    
    # --- Slightly Negative ---
    ("ไม่ค่อยดีเท่าไร", 0.05, 0.40, 1.0),
    ("ผิดอีกแล้ว", 0.00, 0.50, 1.1),
    ("ไม่ใช่แบบนี้", 0.05, 0.45, 1.0),
    ("ทำไมไม่เข้าใจ", 0.00, 0.55, 1.1),
    ("เบื่อจัง", 0.00, 0.40, 0.9),
    ("น่าผิดหวัง", 0.00, 0.50, 1.0),
    
    # --- Very Negative ---
    ("ห่วยแตก!", 0.00, 0.80, 1.2),
    ("โง่ชะมัด", 0.00, 0.85, 1.3),
    ("ไร้สาระ!", 0.00, 0.70, 1.1),
    ("ไม่เอาแล้ว!", 0.00, 0.75, 1.2),
    ("กากมาก", 0.00, 0.80, 1.2),
    
    # --- Mixed ---
    ("ก็ดีนะ แต่ยังไม่ใช่", 0.30, 0.35, 1.0),
    ("ขอบคุณ แต่ผิดนะ", 0.40, 0.40, 1.0),
    ("เก่งขึ้นนะ แต่ยังไม่พอ", 0.35, 0.30, 1.0),
    ("โอเค แต่ครั้งหน้าทำให้ดีกว่านี้", 0.25, 0.30, 1.0),
    ("ไม่เลว", 0.30, 0.15, 0.9),
]
