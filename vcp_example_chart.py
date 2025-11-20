"""
VCP Pattern Example Chart Creator
================================
Create a conceptual example of what a VCP pattern looks like
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import seaborn as sns

# Set clean style
plt.style.use('seaborn-v0_8')

def create_vcp_example_chart():
    """Create a conceptual VCP pattern example for education"""
    
    print("📚 Creating VCP Pattern Example Chart...")
    
    # Create synthetic data that shows a perfect VCP pattern
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    np.random.seed(42)  # For reproducible results
    
    # Phase 1: Uptrend leading to base (Jan-Mar)
    phase1_days = 90
    uptrend = np.linspace(100, 150, phase1_days) + np.random.normal(0, 2, phase1_days)
    
    # Phase 2: VCP Base formation (Apr-Nov)
    base_days = 240
    base_start = 150
    
    # Create contractions with decreasing volatility
    contraction1 = create_contraction(base_start, 60, 0.15, 0.08)  # 15% down, 8% recovery
    contraction2 = create_contraction(contraction1[-1], 45, 0.12, 0.06)  # 12% down, 6% recovery  
    contraction3 = create_contraction(contraction2[-1], 40, 0.08, 0.04)  # 8% down, 4% recovery
    contraction4 = create_contraction(contraction3[-1], 35, 0.05, 0.02)  # 5% down, 2% recovery
    
    # Combine contractions
    base = np.concatenate([contraction1, contraction2, contraction3, contraction4])
    
    # Phase 3: Breakout (Dec)
    breakout_days = len(dates) - len(uptrend) - len(base)
    breakout = np.linspace(base[-1], base[-1] * 1.25, breakout_days) + np.random.normal(0, 1, breakout_days)
    
    # Combine all phases
    price = np.concatenate([uptrend, base, breakout])
    price = price[:len(dates)]  # Ensure same length
    
    # Create volume data (lower during contractions)
    volume = create_volume_profile(len(dates))
    
    # Create the chart
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), height_ratios=[3, 1])
    
    # Plot price chart
    ax1.plot(dates, price, linewidth=2.5, color='#2E86AB', label='Stock Price')
    
    # Add moving averages
    ma20 = pd.Series(price).rolling(20, min_periods=1).mean()
    ma50 = pd.Series(price).rolling(50, min_periods=1).mean()
    
    ax1.plot(dates, ma20, '--', alpha=0.7, color='orange', linewidth=1.5, label='20-day MA')
    ax1.plot(dates, ma50, '--', alpha=0.7, color='red', linewidth=1.5, label='50-day MA')
    
    # Annotate VCP phases
    annotate_vcp_phases(ax1, dates, price)
    
    # Format price chart
    ax1.set_ylabel('Stock Price ($)', fontsize=12, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.set_title('VCP Pattern Example - Complete Cycle', fontsize=16, fontweight='bold')
    
    # Plot volume chart
    colors = ['green' if i % 4 != 0 else 'red' for i in range(len(volume))]
    ax2.bar(dates, volume, color=colors, alpha=0.6, width=1)
    
    vol_ma = pd.Series(volume).rolling(20, min_periods=1).mean()
    ax2.plot(dates, vol_ma, color='black', linewidth=2, label='Volume MA(20)')
    
    ax2.set_ylabel('Volume', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.set_title('Volume Profile (Notice decreasing volume during contractions)', fontsize=12)
    
    plt.tight_layout()
    
    # Save chart
    save_path = 'charts/VCP_Pattern_Example_Educational.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✅ VCP example chart saved: {save_path}")
    
    plt.show()
    return save_path

def create_contraction(start_price, days, down_pct, recovery_pct):
    """Create a single contraction cycle"""
    
    # Down phase (2/3 of days)
    down_days = int(days * 0.6)
    low_price = start_price * (1 - down_pct)
    down_phase = np.linspace(start_price, low_price, down_days)
    down_phase += np.random.normal(0, start_price * 0.01, down_days)  # Add noise
    
    # Recovery phase (1/3 of days)
    up_days = days - down_days
    recovery_price = low_price * (1 + recovery_pct)
    up_phase = np.linspace(low_price, recovery_price, up_days)
    up_phase += np.random.normal(0, start_price * 0.008, up_days)  # Less noise
    
    return np.concatenate([down_phase, up_phase])

def create_volume_profile(total_days):
    """Create volume profile that decreases during contractions"""
    
    base_volume = 100000
    
    # High volume during uptrend (first 90 days)
    uptrend_vol = np.random.normal(base_volume * 1.5, base_volume * 0.3, 90)
    
    # Decreasing volume during base formation
    # Each contraction has lower volume
    c1_vol = np.random.normal(base_volume * 1.2, base_volume * 0.2, 60)  # Contraction 1
    c2_vol = np.random.normal(base_volume * 0.9, base_volume * 0.15, 60) # Contraction 2
    c3_vol = np.random.normal(base_volume * 0.7, base_volume * 0.1, 60)  # Contraction 3
    c4_vol = np.random.normal(base_volume * 0.5, base_volume * 0.08, 60) # Contraction 4
    
    # High volume on breakout
    breakout_days = total_days - 90 - 240
    breakout_vol = np.random.normal(base_volume * 2.0, base_volume * 0.4, breakout_days)
    
    volume = np.concatenate([uptrend_vol, c1_vol, c2_vol, c3_vol, c4_vol, breakout_vol])
    
    # Ensure positive values
    volume = np.abs(volume)
    
    return volume[:total_days]

def annotate_vcp_phases(ax, dates, price):
    """Add annotations explaining each phase of the VCP"""
    
    # Phase 1: Uptrend
    ax.annotate('Phase 1: UPTREND\nStock in strong upward move', 
               xy=(dates[45], price[45]), xytext=(dates[45], price[45] + 20),
               fontsize=11, fontweight='bold', color='green',
               bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.8),
               arrowprops=dict(arrowstyle='->', color='green'))
    
    # Phase 2: VCP Base
    base_start = 90
    base_end = 330
    
    # Highlight base area
    ax.axvspan(dates[base_start], dates[base_end], alpha=0.15, color='blue', label='VCP Base Formation')
    
    ax.annotate('Phase 2: VCP BASE FORMATION\nMultiple contractions with\ndecreasing volatility', 
               xy=(dates[210], price[210]), xytext=(dates[150], price[210] + 25),
               fontsize=11, fontweight='bold', color='blue',
               bbox=dict(boxstyle="round,pad=0.4", facecolor='lightblue', alpha=0.8),
               arrowprops=dict(arrowstyle='->', color='blue'))
    
    # Mark individual contractions
    contraction_points = [120, 180, 240, 300]
    for i, point in enumerate(contraction_points, 1):
        if point < len(dates):
            ax.annotate(f'C{i}', xy=(dates[point], price[point]), 
                       xytext=(dates[point], price[point] + 8),
                       fontsize=10, ha='center', fontweight='bold',
                       bbox=dict(boxstyle="circle,pad=0.1", facecolor='yellow', alpha=0.8))
    
    # Phase 3: Breakout
    if len(dates) > 330:
        ax.annotate('Phase 3: BREAKOUT\nStock breaks to new highs\nwith volume expansion', 
                   xy=(dates[350], price[350]), xytext=(dates[320], price[350] + 15),
                   fontsize=11, fontweight='bold', color='red',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor='yellow', alpha=0.9),
                   arrowprops=dict(arrowstyle='->', color='red'))
    
    # Add resistance line
    resistance_level = np.max(price[base_start:base_end])
    ax.axhline(y=resistance_level, color='red', linestyle='--', linewidth=2, alpha=0.8,
              label=f'Resistance/Breakout Level: ${resistance_level:.1f}')

def create_simple_explanation():
    """Create a simple text explanation of the pattern"""
    
    explanation = """
SIMPLE VCP PATTERN EXPLANATION
=============================

Think of VCP like a coiled spring:

1. UPTREND PHASE (Green area):
   - Stock moves up strongly
   - Attracts attention from investors
   - Volume is high

2. BASE FORMATION PHASE (Blue area):
   - Stock takes a "rest" from the uptrend  
   - Creates 3-4 pullbacks (contractions)
   - Each pullback gets SMALLER (like a coiled spring)
   - Volume DECREASES during pullbacks (weak hands selling)
   - This is the VCP pattern forming

3. BREAKOUT PHASE (Yellow area):
   - Stock breaks above the highest point of the base
   - Volume INCREASES (strong hands buying)
   - Like a coiled spring being released
   - This is where profits can be made

KEY POINTS TO REMEMBER:
- Each contraction should be smaller than the last one
- Volume should dry up during contractions  
- The pattern can take 2-6 months to form
- Quality patterns have 3+ contractions
- Best patterns occur after a significant uptrend

TRADING RULES:
- Only buy AFTER breakout above resistance
- Use increased volume to confirm breakout
- Set stop loss below the last contraction low
- Target 20-30% gains from breakout point

This is educational content only - not investment advice!
    """
    
    with open('charts/VCP_Simple_Explanation.txt', 'w', encoding='utf-8') as f:
        f.write(explanation)
    
    print("📝 Simple explanation saved: charts/VCP_Simple_Explanation.txt")

if __name__ == "__main__":
    print("🎓 VCP EDUCATIONAL CHART CREATOR")
    print("=" * 40)
    
    # Create example chart
    chart_path = create_vcp_example_chart()
    
    # Create simple explanation
    create_simple_explanation()
    
    print(f"\n✅ EDUCATIONAL MATERIALS CREATED!")
    print(f"📊 Example Chart: {chart_path}")
    print(f"📖 Guide: charts/VCP_Pattern_Guide.txt")  
    print(f"📝 Simple Explanation: charts/VCP_Simple_Explanation.txt")
    print(f"\n💡 These materials will help you understand VCP patterns!")