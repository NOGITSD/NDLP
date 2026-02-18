"""
EVC v2 Evaluation Mode
======================
Runs 100 random conversation turns and generates:
- Hormone movement chart (8 lines over time)
- Emotion movement chart (8 lines over time)
- Trust movement chart
- Per-turn summary table
- Final analysis report

Usage:
    python eval_mode.py
    python eval_mode.py --turns 200
    python eval_mode.py --personality sensitive
"""

import argparse
import random
import json
import os
import numpy as np

# Matplotlib setup (non-interactive backend for saving)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from evc_core import EVCEngine
from config import (
    EVAL_MESSAGES, HORMONE_NAMES, EMOTION_NAMES,
    PERSONALITY_DEFAULT, PERSONALITY_SENSITIVE,
    PERSONALITY_CALM, PERSONALITY_CHEERFUL,
    TRUST_INITIAL
)

# ============================================================
# THAI-FRIENDLY FONT SETUP
# ============================================================

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# COLOR PALETTES
# ============================================================

HORMONE_COLORS = [
    '#FF6B6B',  # Dopamine — red/warm
    '#4ECDC4',  # Serotonin — teal
    '#FF69B4',  # Oxytocin — pink
    '#F7DC6F',  # Endorphin — yellow
    '#E74C3C',  # Cortisol — dark red
    '#F39C12',  # Adrenaline — orange
    '#3498DB',  # GABA — blue
    '#9B59B6',  # Norepinephrine — purple
]

EMOTION_COLORS = [
    '#FFD700',  # Joy — gold
    '#87CEEB',  # Serenity — sky blue
    '#FF69B4',  # Love — pink
    '#FF4500',  # Excitement — orange-red
    '#4169E1',  # Sadness — royal blue
    '#800080',  # Fear — purple
    '#DC143C',  # Anger — crimson
    '#00CED1',  # Surprise — dark turquoise
]


def run_evaluation(num_turns: int = 100, personality_name: str = "default",
                   output_dir: str = "eval_output", seed: int = 42):
    """
    Run full evaluation simulation.
    
    Args:
        num_turns: Number of conversation turns to simulate
        personality_name: "default", "sensitive", "calm", "cheerful"
        output_dir: Directory to save charts and reports
        seed: Random seed for reproducibility
    """
    random.seed(seed)
    np.random.seed(seed)
    
    # Select personality
    personalities = {
        "default": PERSONALITY_DEFAULT,
        "sensitive": PERSONALITY_SENSITIVE,
        "calm": PERSONALITY_CALM,
        "cheerful": PERSONALITY_CHEERFUL,
    }
    personality = personalities.get(personality_name, PERSONALITY_DEFAULT)
    
    # Create engine
    engine = EVCEngine(personality=personality, name=f"Jarvis-{personality_name}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # =============================================
    # RUN SIMULATION
    # =============================================
    print(f"\n{'='*70}")
    print(f"  EVC v2 EVALUATION MODE")
    print(f"  Personality: {personality_name}")
    print(f"  Turns: {num_turns}")
    print(f"  Seed: {seed}")
    print(f"{'='*70}\n")
    
    results = []
    
    for i in range(num_turns):
        # Pick random message
        msg, S, D, C = random.choice(EVAL_MESSAGES)
        
        # Add slight randomness to S, D values (±0.05)
        S = np.clip(S + random.uniform(-0.05, 0.05), 0, 1)
        D = np.clip(D + random.uniform(-0.05, 0.05), 0, 1)
        
        # Process turn
        result = engine.process_turn(S, D, C, message=msg)
        results.append(result)
        
        # Print every 10 turns
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  Turn {result['turn']:3d}: "
                  f"S={S:.2f} D={D:.2f} | "
                  f"{result['emotion_blend']} | "
                  f"Trust: {result['trust']:.2f}")
    
    # =============================================
    # GENERATE CHARTS
    # =============================================
    print(f"\n{'='*70}")
    print(f"  GENERATING CHARTS...")
    print(f"{'='*70}\n")
    
    hormone_history = engine.hormones.get_history_array()  # (turns+1, 8)
    emotion_history = engine.emotions.get_history_array()   # (turns, 8)
    turns_x = np.arange(len(hormone_history))
    turns_x_emo = np.arange(1, len(emotion_history) + 1)
    
    # ----- Chart 1: Hormone Levels Over Time -----
    fig, ax = plt.subplots(figsize=(16, 8))
    for i in range(8):
        ax.plot(turns_x, hormone_history[:, i],
                color=HORMONE_COLORS[i], linewidth=1.5,
                label=HORMONE_NAMES[i], alpha=0.85)
    
    ax.set_xlabel('Turn', fontsize=12)
    ax.set_ylabel('Hormone Level [0-1]', fontsize=12)
    ax.set_title(f'EVC v2 - Hormone Dynamics Over {num_turns} Turns (Personality: {personality_name})',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10, ncol=2)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, num_turns)
    
    plt.tight_layout()
    hormone_chart_path = os.path.join(output_dir, 'hormones_chart.png')
    fig.savefig(hormone_chart_path, dpi=150)
    plt.close(fig)
    print(f"  [SAVED] {hormone_chart_path}")
    
    # ----- Chart 2: Emotion Levels Over Time -----
    fig, ax = plt.subplots(figsize=(16, 8))
    for i in range(8):
        ax.plot(turns_x_emo, emotion_history[:, i],
                color=EMOTION_COLORS[i], linewidth=1.5,
                label=EMOTION_NAMES[i], alpha=0.85)
    
    ax.set_xlabel('Turn', fontsize=12)
    ax.set_ylabel('Emotion Score (Normalized)', fontsize=12)
    ax.set_title(f'EVC v2 - Emotion Distribution Over {num_turns} Turns (Personality: {personality_name})',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10, ncol=2)
    ax.set_ylim(-0.05, 0.6)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(1, num_turns)
    
    plt.tight_layout()
    emotion_chart_path = os.path.join(output_dir, 'emotions_chart.png')
    fig.savefig(emotion_chart_path, dpi=150)
    plt.close(fig)
    print(f"  [SAVED] {emotion_chart_path}")
    
    # ----- Chart 3: Stacked Area — Emotion Composition -----
    fig, ax = plt.subplots(figsize=(16, 6))
    ax.stackplot(turns_x_emo, emotion_history.T,
                 labels=EMOTION_NAMES, colors=EMOTION_COLORS, alpha=0.8)
    
    ax.set_xlabel('Turn', fontsize=12)
    ax.set_ylabel('Emotion Proportion', fontsize=12)
    ax.set_title(f'EVC v2 - Emotion Composition (Stacked Area)',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=9, ncol=4)
    ax.set_ylim(0, 1.05)
    ax.set_xlim(1, num_turns)
    ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    stacked_chart_path = os.path.join(output_dir, 'emotions_stacked.png')
    fig.savefig(stacked_chart_path, dpi=150)
    plt.close(fig)
    print(f"  [SAVED] {stacked_chart_path}")
    
    # ----- Chart 4: Trust Level Over Time -----
    trust_values = [r['trust'] for r in results]
    fig, ax = plt.subplots(figsize=(16, 4))
    ax.plot(range(1, num_turns + 1), trust_values,
            color='#2ECC71', linewidth=2, label='Trust Level')
    ax.fill_between(range(1, num_turns + 1), trust_values,
                    alpha=0.2, color='#2ECC71')
    ax.set_xlabel('Turn', fontsize=12)
    ax.set_ylabel('Trust [0-1]', fontsize=12)
    ax.set_title('Trust Level Over Time', fontsize=14, fontweight='bold')
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(1, num_turns)
    
    plt.tight_layout()
    trust_chart_path = os.path.join(output_dir, 'trust_chart.png')
    fig.savefig(trust_chart_path, dpi=150)
    plt.close(fig)
    print(f"  [SAVED] {trust_chart_path}")
    
    # ----- Chart 5: Combined Dashboard -----
    fig, axes = plt.subplots(4, 1, figsize=(18, 20), 
                              gridspec_kw={'height_ratios': [3, 3, 2, 1.5]})
    
    # Panel 1: Hormones
    for i in range(8):
        axes[0].plot(turns_x, hormone_history[:, i],
                     color=HORMONE_COLORS[i], linewidth=1.2,
                     label=HORMONE_NAMES[i])
    axes[0].set_ylabel('Hormone Level')
    axes[0].set_title(f'EVC v2 Dashboard — {personality_name} personality, {num_turns} turns',
                      fontsize=16, fontweight='bold')
    axes[0].legend(loc='upper right', fontsize=8, ncol=4)
    axes[0].set_ylim(-0.05, 1.05)
    axes[0].grid(True, alpha=0.3)
    
    # Panel 2: Emotions
    for i in range(8):
        axes[1].plot(turns_x_emo, emotion_history[:, i],
                     color=EMOTION_COLORS[i], linewidth=1.2,
                     label=EMOTION_NAMES[i])
    axes[1].set_ylabel('Emotion Score')
    axes[1].legend(loc='upper right', fontsize=8, ncol=4)
    axes[1].set_ylim(-0.05, 0.6)
    axes[1].grid(True, alpha=0.3)
    
    # Panel 3: Stacked Emotion
    axes[2].stackplot(turns_x_emo, emotion_history.T,
                      colors=EMOTION_COLORS, alpha=0.7)
    axes[2].set_ylabel('Emotion Mix')
    axes[2].set_ylim(0, 1.05)
    axes[2].grid(True, alpha=0.2)
    
    # Panel 4: Trust
    axes[3].plot(range(1, num_turns + 1), trust_values,
                 color='#2ECC71', linewidth=2)
    axes[3].fill_between(range(1, num_turns + 1), trust_values,
                         alpha=0.2, color='#2ECC71')
    axes[3].set_ylabel('Trust')
    axes[3].set_xlabel('Turn')
    axes[3].set_ylim(-0.05, 1.05)
    axes[3].grid(True, alpha=0.3)
    
    for ax in axes:
        ax.set_xlim(0, num_turns)
    
    plt.tight_layout()
    dashboard_path = os.path.join(output_dir, 'dashboard.png')
    fig.savefig(dashboard_path, dpi=150)
    plt.close(fig)
    print(f"  [SAVED] {dashboard_path}")
    
    # =============================================
    # GENERATE REPORT
    # =============================================
    print(f"\n{'='*70}")
    print(f"  GENERATING REPORT...")
    print(f"{'='*70}\n")
    
    report_lines = []
    report_lines.append("=" * 70)
    report_lines.append("  EVC v2 EVALUATION REPORT")
    report_lines.append("=" * 70)
    report_lines.append(f"  Personality: {personality_name}")
    report_lines.append(f"  Total Turns: {num_turns}")
    report_lines.append(f"  Random Seed: {seed}")
    report_lines.append("")
    
    # Hormone statistics
    report_lines.append("-" * 70)
    report_lines.append("  HORMONE STATISTICS")
    report_lines.append("-" * 70)
    report_lines.append(f"  {'Hormone':<18} {'Mean':>8} {'StdDev':>8} {'Min':>8} {'Max':>8} {'Final':>8}")
    report_lines.append(f"  {'-'*16:<18} {'---':>8} {'---':>8} {'---':>8} {'---':>8} {'---':>8}")
    
    for i in range(8):
        h_data = hormone_history[1:, i]  # skip initial state
        report_lines.append(
            f"  {HORMONE_NAMES[i]:<18} "
            f"{h_data.mean():>8.4f} "
            f"{h_data.std():>8.4f} "
            f"{h_data.min():>8.4f} "
            f"{h_data.max():>8.4f} "
            f"{h_data[-1]:>8.4f}"
        )
    
    report_lines.append("")
    
    # Emotion statistics
    report_lines.append("-" * 70)
    report_lines.append("  EMOTION STATISTICS")
    report_lines.append("-" * 70)
    report_lines.append(f"  {'Emotion':<18} {'Mean':>8} {'StdDev':>8} {'Min':>8} {'Max':>8} {'Final':>8}")
    report_lines.append(f"  {'-'*16:<18} {'---':>8} {'---':>8} {'---':>8} {'---':>8} {'---':>8}")
    
    for i in range(8):
        e_data = emotion_history[:, i]
        report_lines.append(
            f"  {EMOTION_NAMES[i]:<18} "
            f"{e_data.mean():>8.4f} "
            f"{e_data.std():>8.4f} "
            f"{e_data.min():>8.4f} "
            f"{e_data.max():>8.4f} "
            f"{e_data[-1]:>8.4f}"
        )
    
    report_lines.append("")
    
    # Dominant emotion count
    report_lines.append("-" * 70)
    report_lines.append("  DOMINANT EMOTION FREQUENCY")
    report_lines.append("-" * 70)
    
    dom_counts = {}
    for r in results:
        dom = r['dominant_emotion']
        dom_counts[dom] = dom_counts.get(dom, 0) + 1
    
    for emo, count in sorted(dom_counts.items(), key=lambda x: -x[1]):
        bar = "█" * int(count / num_turns * 40)
        report_lines.append(f"  {emo:<18} {count:>4} ({count/num_turns*100:>5.1f}%) {bar}")
    
    report_lines.append("")
    
    # Trust summary
    report_lines.append("-" * 70)
    report_lines.append("  TRUST SUMMARY")
    report_lines.append("-" * 70)
    trust_arr = np.array(trust_values)
    report_lines.append(f"  Initial: {TRUST_INITIAL:.2f}")
    report_lines.append(f"  Final:   {trust_arr[-1]:.4f}")
    report_lines.append(f"  Mean:    {trust_arr.mean():.4f}")
    report_lines.append(f"  Min:     {trust_arr.min():.4f}")
    report_lines.append(f"  Max:     {trust_arr.max():.4f}")
    
    report_lines.append("")
    
    # Turn-by-turn detail (first 20 + last 10)
    report_lines.append("-" * 70)
    report_lines.append("  TURN-BY-TURN DETAIL (First 20 + Last 10)")
    report_lines.append("-" * 70)
    report_lines.append(f"  {'Turn':>4} {'S':>5} {'D':>5} {'Dominant':<12} {'Score':>6} {'Trust':>6} Message")
    report_lines.append(f"  {'----':>4} {'---':>5} {'---':>5} {'--------':<12} {'-----':>6} {'-----':>6} -------")
    
    show_turns = list(range(min(20, len(results)))) + list(range(max(0, len(results)-10), len(results)))
    show_turns = sorted(set(show_turns))
    
    prev_idx = -1
    for idx in show_turns:
        if prev_idx >= 0 and idx - prev_idx > 1:
            report_lines.append(f"  {'...':>4}")
        r = results[idx]
        report_lines.append(
            f"  {r['turn']:>4} "
            f"{r['input']['S']:>5.2f} "
            f"{r['input']['D']:>5.2f} "
            f"{r['dominant_emotion']:<12} "
            f"{r['dominant_score']:>6.3f} "
            f"{r['trust']:>6.3f} "
            f"{r['message'][:30]}"
        )
        prev_idx = idx
    
    report_lines.append("")
    report_lines.append("=" * 70)
    report_lines.append("  END OF REPORT")
    report_lines.append("=" * 70)
    
    # Print report
    report_text = "\n".join(report_lines)
    print(report_text)
    
    # Save report
    report_path = os.path.join(output_dir, 'eval_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_text)
    print(f"\n  [SAVED] {report_path}")
    
    # Save full JSON log
    json_path = os.path.join(output_dir, 'eval_log.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  [SAVED] {json_path}")
    
    print(f"\n  All outputs saved to: {os.path.abspath(output_dir)}/")
    print(f"  Charts: hormones_chart.png, emotions_chart.png, emotions_stacked.png,")
    print(f"          trust_chart.png, dashboard.png")
    print(f"  Report: eval_report.txt, eval_log.json\n")
    
    return results


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EVC v2 Evaluation Mode")
    parser.add_argument("--turns", type=int, default=100,
                        help="Number of turns to simulate (default: 100)")
    parser.add_argument("--personality", type=str, default="default",
                        choices=["default", "sensitive", "calm", "cheerful"],
                        help="Personality profile (default: default)")
    parser.add_argument("--output", type=str, default="eval_output",
                        help="Output directory (default: eval_output)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    
    args = parser.parse_args()
    
    run_evaluation(
        num_turns=args.turns,
        personality_name=args.personality,
        output_dir=args.output,
        seed=args.seed,
    )
