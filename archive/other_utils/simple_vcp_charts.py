"""
Simple VCP Pattern Visualization
===============================
Create easy-to-understand charts with clear annotations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import numpy as np
from datetime import date, timedelta
from volatility_patterns.data.data_service import DataService
from volatility_patterns.core.vcp_detector import VCPDetector
import seaborn as sns

# Set style for clean, easy to read charts
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class SimpleVCPVisualizer:
    """
    Simple, easy-to-understand VCP chart creator
    
    Features:
    - Clean price chart with minimal clutter
    - Clear VCP pattern annotations
    - Easy-to-read legends
    - Highlighted buy zones
    """
    
    def __init__(self):
        self.data_service = DataService()
        self.detector = VCPDetector()
    
    def create_simple_chart(self, symbol: str, save_path: str = None):
        """Create a simple, annotated VCP chart"""
        
        # Get recent data (1 year)
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
        
        print(f"📊 Creating simple chart for {symbol}...")
        
        # Fetch data
        data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
        if len(data) < 50:
            raise ValueError(f"Not enough data for {symbol}")
        
        # Detect patterns
        patterns = self.detector.detect_vcp_patterns(data, symbol)
        best_pattern = max(patterns, key=lambda p: p.quality_score) if patterns else None
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[3, 1])
        
        # Plot 1: Price Chart with VCP annotations
        self._plot_simple_price_chart(ax1, data, best_pattern, symbol)
        
        # Plot 2: Volume Chart
        self._plot_simple_volume_chart(ax2, data, best_pattern)
        
        # Add title and save
        fig.suptitle(f'{symbol} - VCP Pattern Analysis (Simple View)', 
                     fontsize=16, fontweight='bold', y=0.98)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Chart saved: {save_path}")
        
        return fig
    
    def _plot_simple_price_chart(self, ax, data, pattern, symbol):
        """Plot clean price chart with VCP annotations"""
        
        # Basic price line
        ax.plot(data.index, data['close'], linewidth=2, color='#2E86AB', label='Price')
        
        # Add moving averages for context
        ma20 = data['close'].rolling(20).mean()
        ma50 = data['close'].rolling(50).mean()
        
        ax.plot(data.index, ma20, '--', alpha=0.7, color='orange', linewidth=1, label='20-day MA')
        ax.plot(data.index, ma50, '--', alpha=0.7, color='red', linewidth=1, label='50-day MA')
        
        if pattern:
            self._annotate_vcp_pattern(ax, data, pattern)
        else:
            # Add text box explaining no pattern found
            ax.text(0.02, 0.98, 'No VCP Pattern Detected\n(Try lower quality threshold)', 
                   transform=ax.transAxes, fontsize=12, 
                   bbox=dict(boxstyle="round,pad=0.3", facecolor='yellow', alpha=0.7),
                   verticalalignment='top')
        
        ax.set_ylabel('Price (₹)', fontsize=12, fontweight='bold')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.set_title(f'{symbol} Stock Price with VCP Analysis', fontsize=14, fontweight='bold')
    
    def _annotate_vcp_pattern(self, ax, data, pattern):
        """Add clear VCP pattern annotations"""
        
        # Highlight the base period
        base_start = pattern.base_start_date
        base_end = pattern.base_end_date
        
        # Get price range for the base
        base_data = data[(data.index >= base_start) & (data.index <= base_end)]
        base_high = base_data['high'].max()
        base_low = base_data['low'].min()
        
        # Draw base rectangle
        ax.axvspan(base_start, base_end, alpha=0.2, color='green', label='VCP Base Period')
        
        # Mark contractions
        for i, contraction in enumerate(pattern.contractions):
            if i < 5:  # Only show first 5 for clarity
                # Mark contraction period
                ax.axvspan(contraction.start_date, contraction.end_date, 
                          alpha=0.3, color='blue', linewidth=0)
                
                # Add contraction number
                mid_date = contraction.start_date + (contraction.end_date - contraction.start_date) / 2
                ax.annotate(f'C{i+1}', xy=(mid_date, base_high), 
                           xytext=(mid_date, base_high + (base_high - base_low) * 0.1),
                           fontsize=10, ha='center', fontweight='bold',
                           bbox=dict(boxstyle="round,pad=0.2", facecolor='lightblue'))
        
        # Add pattern info box
        info_text = f"""VCP Pattern Detected!
Quality Score: {pattern.quality_score:.1f}
Stage: {pattern.current_stage}
Contractions: {len(pattern.contractions)}
Duration: {pattern.base_duration} days"""
        
        ax.text(0.98, 0.98, info_text, transform=ax.transAxes, fontsize=11,
               bbox=dict(boxstyle="round,pad=0.5", facecolor='lightgreen', alpha=0.8),
               verticalalignment='top', horizontalalignment='right')
        
        # Mark potential buy zone (if pattern is complete)
        if pattern.is_setup_complete:
            current_price = data['close'].iloc[-1]
            resistance = base_high
            
            # Draw buy zone line
            ax.axhline(y=resistance, color='red', linestyle='--', linewidth=2, 
                      label=f'Breakout Level: ₹{resistance:.1f}')
            
            # Add buy zone annotation
            ax.annotate('🎯 POTENTIAL BUY ZONE\n(Above breakout level)', 
                       xy=(data.index[-20], resistance),
                       xytext=(data.index[-20], resistance * 1.05),
                       fontsize=12, fontweight='bold', color='red',
                       bbox=dict(boxstyle="round,pad=0.3", facecolor='yellow', alpha=0.8),
                       arrowprops=dict(arrowstyle='->', color='red', lw=2))
    
    def _plot_simple_volume_chart(self, ax, data, pattern):
        """Plot simple volume chart"""
        
        # Volume bars
        colors = ['green' if close >= open_price else 'red' 
                 for close, open_price in zip(data['close'], data['open'])]
        
        ax.bar(data.index, data['volume'], color=colors, alpha=0.7, width=1)
        
        # Volume moving average
        vol_ma = data['volume'].rolling(20).mean()
        ax.plot(data.index, vol_ma, color='black', linewidth=2, label='Volume MA(20)')
        
        if pattern:
            # Highlight low volume during contractions
            for contraction in pattern.contractions[:3]:  # Show first 3
                ax.axvspan(contraction.start_date, contraction.end_date, 
                          alpha=0.2, color='blue')
        
        ax.set_ylabel('Volume', fontsize=12, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_title('Volume Analysis (Low volume during contractions is good)', fontsize=12)

def create_educational_charts():
    """Create educational charts for top VCP patterns"""
    
    print("📚 CREATING EDUCATIONAL VCP CHARTS")
    print("=" * 50)
    print("These charts are designed to be easy to understand:")
    print("• Simple price line (no complex candles)")
    print("• Clear annotations for VCP patterns")
    print("• Educational labels and explanations")
    print("• Highlighted buy zones")
    
    visualizer = SimpleVCPVisualizer()
    
    # Create charts for top patterns found
    top_symbols = ['HDFCBANK', 'CIPLA', 'BAJAJFINSV', 'BIOCON']
    
    for i, symbol in enumerate(top_symbols, 1):
        try:
            print(f"\n[{i}/4] Creating educational chart for {symbol}...")
            
            chart_path = f"charts/simple_vcp_{symbol}_educational.png"
            fig = visualizer.create_simple_chart(symbol, chart_path)
            
            # Close figure to save memory
            plt.close(fig)
            
        except Exception as e:
            print(f"❌ Failed to create chart for {symbol}: {e}")
    
    # Create explanation guide
    create_vcp_explanation_guide()
    
    print(f"\n🎉 EDUCATIONAL CHARTS COMPLETE!")
    print("Check charts/ directory for simple, annotated VCP charts")

def create_vcp_explanation_guide():
    """Create a text guide explaining VCP patterns"""
    
    guide_content = """
VCP PATTERN EXPLANATION GUIDE
============================

What is a VCP (Volatility Contracting Pattern)?
-----------------------------------------------
A VCP is a chart pattern where:
1. Stock builds a "base" over several weeks/months
2. During this base, volatility contracts (price swings get smaller)  
3. Each pullback is smaller than the previous one
4. Volume dries up during pullbacks
5. Eventually, stock breaks out to new highs

How to Read the VCP Charts:
--------------------------

GREEN SHADED AREA = VCP Base Period
   This is where the pattern is forming

BLUE SHADED AREAS = Contractions (C1, C2, C3...)
   Each contraction should be smaller than the previous

VOLUME BARS = Trading Activity
   Volume should decrease during contractions
   Green bars = up days, Red bars = down days

RED DASHED LINE = Breakout Level
   This is where you might consider buying
   Wait for stock to break above this level with volume

MOVING AVERAGES = Trend Context
   Orange line = 20-day average (short-term trend)
   Red line = 50-day average (medium-term trend)

What Makes a Good VCP Pattern?
-----------------------------
- 3+ contractions with decreasing volatility
- Each pullback shallower than the last
- Volume dries up during pullbacks  
- Stock holds above key moving averages
- Quality score above 70

Trading the VCP:
----------------
1. Wait for breakout above resistance (red line)
2. Look for increased volume on breakout
3. Set stop loss below the last contraction low
4. Target: 20-30% gain from breakout point

Risk Warning:
------------
- This is educational content only
- Past patterns don't guarantee future results
- Always use proper risk management
- Consider consulting a financial advisor

Generated on: November 16, 2025
"""
    
    with open('charts/VCP_Pattern_Guide.txt', 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print("📖 VCP explanation guide saved: charts/VCP_Pattern_Guide.txt")

if __name__ == "__main__":
    create_educational_charts()