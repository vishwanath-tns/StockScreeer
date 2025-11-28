"""
VCP Educational Chart - Clear Volatility Contraction Visualization
================================================================
Create a chart that clearly shows what volatility contraction means with measurements
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

# Set clean style
plt.style.use('seaborn-v0_8')

class VCPEducationalChart:
    """Create educational charts showing clear volatility contraction principles"""
    
    def __init__(self):
        self.data_service = DataService()
        self.detector = VCPDetector()
        
    def create_educational_vcp_chart(self, symbol):
        """Create an educational chart explaining volatility contraction"""
        
        try:
            print(f"📚 Creating VCP educational chart for {symbol}...")
            
            # Get data
            end_date = date.today()
            start_date = date(end_date.year - 1, 1, 1)
            
            data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
            data = self._filter_trading_days(data)
            
            if len(data) < 100:
                print(f"   ❌ Insufficient data: only {len(data)} records")
                return None
            
            # Detect patterns
            patterns = self.detector.detect_vcp_patterns(data, symbol)
            
            if not patterns:
                print(f"   ❌ No patterns found")
                return None
            
            # Get best pattern
            best_pattern = max(patterns, key=lambda p: p.quality_score)
            print(f"✅ Found pattern (Quality: {best_pattern.quality_score:.1f})")
            
            # Focus on recent contractions
            cutoff_date = date.today() - timedelta(days=180)
            recent_contractions = [
                c for c in best_pattern.contractions 
                if c.end_date >= cutoff_date
            ]
            
            if not recent_contractions:
                recent_contractions = best_pattern.contractions[-4:] if len(best_pattern.contractions) > 4 else best_pattern.contractions
            
            if not recent_contractions:
                print(f"   ❌ No recent contractions found")
                return None
            
            # Calculate timeframe
            first_recent = min(c.start_date for c in recent_contractions)
            last_recent = max(c.end_date for c in recent_contractions)
            
            buffer_days = 21
            focus_start = first_recent - timedelta(days=buffer_days)
            focus_end = last_recent + timedelta(days=buffer_days)
            
            # Get focused data
            focused_data = self.data_service.get_ohlcv_data(symbol, focus_start, focus_end)
            focused_data = self._filter_trading_days(focused_data)
            
            print(f"   Educational focus: {focus_start} to {focus_end} ({len(focused_data)} trading days)")
            
            # Create educational chart
            fig = self._create_educational_chart(focused_data, best_pattern, recent_contractions, symbol)
            
            # Save chart
            save_path = f"charts/vcp_educational_{symbol}.png"
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Educational chart saved: {save_path}")
            return save_path
            
        except Exception as e:
            print(f"❌ Error creating educational chart for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _filter_trading_days(self, data):
        """Filter out weekends"""
        data['date'] = pd.to_datetime(data['date'])
        data = data[data['date'].dt.dayofweek < 5].copy()
        return data.reset_index(drop=True)
    
    def _create_educational_chart(self, data, pattern, recent_contractions, symbol):
        """Create the educational chart with clear explanations"""
        
        fig = plt.figure(figsize=(20, 16))
        
        # Create layout: Main chart (top), Measurements (middle), Explanation (bottom)
        gs = fig.add_gridspec(4, 2, height_ratios=[3, 1, 1, 1], width_ratios=[3, 1], 
                             hspace=0.3, wspace=0.2)
        
        ax_main = fig.add_subplot(gs[0, :])  # Main chart spans both columns
        ax_volume = fig.add_subplot(gs[1, :])  # Volume spans both columns
        ax_measurements = fig.add_subplot(gs[2, 0])  # Contraction measurements
        ax_explanation = fig.add_subplot(gs[2:, 1])  # Explanation text
        
        # Main title
        fig.suptitle(f'{symbol} - VCP Education: Understanding Volatility Contraction', 
                    fontsize=18, fontweight='bold')
        
        # Plot components
        self._plot_educational_price(ax_main, data, pattern, recent_contractions, symbol)
        self._plot_educational_volume(ax_volume, data, recent_contractions)
        self._plot_contraction_measurements(ax_measurements, data, recent_contractions)
        self._plot_vcp_explanation(ax_explanation)
        
        # Format axes
        self._format_educational_axis(ax_main, data)
        self._format_educational_axis(ax_volume, data)
        
        return fig
    
    def _plot_educational_price(self, ax, data, pattern, recent_contractions, symbol):
        """Plot price with clear volatility contraction explanations"""
        
        # Basic price line
        ax.plot(range(len(data)), data['close'], linewidth=2, color='#1f77b4', 
                label='Close Price', zorder=4)
        
        # Fill high-low range to show volatility
        ax.fill_between(range(len(data)), data['low'], data['high'], 
                       alpha=0.2, color='lightblue', label='Daily Price Range', zorder=1)
        
        # Mark each contraction with measurements
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
        
        for i, contraction in enumerate(recent_contractions):
            color = colors[i % len(colors)]
            
            # Find positions
            start_mask = data['date'] >= pd.to_datetime(contraction.start_date)
            end_mask = data['date'] <= pd.to_datetime(contraction.end_date)
            
            if start_mask.any() and end_mask.any():
                start_pos = data[start_mask].index[0]
                end_pos = data[end_mask].index[-1]
                
                # Highlight contraction period
                ax.axvspan(start_pos, end_pos, alpha=0.2, color=color, zorder=2)
                
                # Calculate contraction statistics
                cont_data = data.iloc[start_pos:end_pos+1]
                if len(cont_data) > 0:
                    high_price = cont_data['high'].max()
                    low_price = cont_data['low'].min()
                    price_range = high_price - low_price
                    range_percent = (price_range / low_price) * 100
                    duration = len(cont_data)
                    
                    # Draw range measurement
                    mid_pos = (start_pos + end_pos) / 2
                    
                    # Vertical line showing range
                    ax.plot([mid_pos, mid_pos], [low_price, high_price], 
                           color=color, linewidth=4, alpha=0.8, zorder=5)
                    
                    # Range measurement text
                    ax.text(mid_pos, high_price + (data['high'].max() * 0.02), 
                           f'C{i+1}\n{range_percent:.1f}%\n{duration}d', 
                           ha='center', va='bottom', fontweight='bold', fontsize=11,
                           bbox=dict(boxstyle="round,pad=0.4", facecolor=color, alpha=0.8))
                    
                    # Add range value annotation
                    range_mid = (high_price + low_price) / 2
                    ax.text(mid_pos + 2, range_mid, f'₹{price_range:.0f}', 
                           ha='left', va='center', fontweight='bold', fontsize=10,
                           bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.9))
        
        # Support and resistance
        if len(recent_contractions) > 0:
            first_cont = recent_contractions[0]
            last_cont = recent_contractions[-1]
            
            pattern_data = data[(data['date'] >= pd.to_datetime(first_cont.start_date)) & 
                              (data['date'] <= pd.to_datetime(last_cont.end_date))]
            
            if len(pattern_data) > 0:
                resistance = pattern_data['high'].max()
                support = pattern_data['low'].min()
                
                ax.axhline(y=resistance, color='red', linestyle='--', linewidth=3, 
                          alpha=0.8, label=f'Resistance: ₹{resistance:.0f}')
                ax.axhline(y=support, color='green', linestyle='--', linewidth=3, 
                          alpha=0.8, label=f'Support: ₹{support:.0f}')
        
        # Add MA20 for trend context
        if len(data) > 20:
            ma20 = data['close'].rolling(20, min_periods=1).mean()
            ax.plot(range(len(data)), ma20, '--', alpha=0.7, color='orange', 
                   linewidth=2, label='MA20 (Trend)')
        
        ax.set_ylabel('Price (₹)', fontsize=14, fontweight='bold')
        ax.legend(loc='upper left', fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.set_title('VCP Pattern: Each Pullback Gets SMALLER (Volatility Contracts)', 
                    fontsize=16, fontweight='bold', color='darkblue')
        
        # Add key insight
        ax.text(0.02, 0.95, 'KEY INSIGHT: Notice how each colored area gets SMALLER in height', 
               transform=ax.transAxes, fontsize=12, fontweight='bold', 
               bbox=dict(boxstyle="round,pad=0.5", facecolor='yellow', alpha=0.8))
    
    def _plot_educational_volume(self, ax, data, recent_contractions):
        """Plot volume showing dry-up during contractions"""
        
        # Volume bars
        colors = ['darkgreen' if close >= open_val else 'darkred' 
                 for close, open_val in zip(data['close'], data['open'])]
        
        ax.bar(range(len(data)), data['volume'], color=colors, alpha=0.6, width=0.8)
        
        # Volume MA
        vol_ma = data['volume'].rolling(10, min_periods=1).mean()
        ax.plot(range(len(data)), vol_ma, color='black', linewidth=3, 
               label='Volume MA(10)', alpha=0.8)
        
        # Highlight contractions
        contraction_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
        
        for i, contraction in enumerate(recent_contractions):
            color = contraction_colors[i % len(contraction_colors)]
            
            start_mask = data['date'] >= pd.to_datetime(contraction.start_date)
            end_mask = data['date'] <= pd.to_datetime(contraction.end_date)
            
            if start_mask.any() and end_mask.any():
                start_pos = data[start_mask].index[0]
                end_pos = data[end_mask].index[-1]
                ax.axvspan(start_pos, end_pos, alpha=0.2, color=color, zorder=1)
        
        ax.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
        
        ax.set_ylabel('Volume', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_title('Volume Should DECREASE During Contractions (Selling Pressure Fades)', 
                    fontsize=14, fontweight='bold', color='darkgreen')
    
    def _plot_contraction_measurements(self, ax, data, recent_contractions):
        """Show contraction measurements in a bar chart"""
        
        if not recent_contractions:
            ax.text(0.5, 0.5, 'No contractions to measure', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12)
            return
        
        # Calculate measurements
        contraction_nums = []
        price_ranges = []
        durations = []
        range_percents = []
        
        for i, contraction in enumerate(recent_contractions):
            start_mask = data['date'] >= pd.to_datetime(contraction.start_date)
            end_mask = data['date'] <= pd.to_datetime(contraction.end_date)
            
            if start_mask.any() and end_mask.any():
                start_pos = data[start_mask].index[0]
                end_pos = data[end_mask].index[-1]
                
                cont_data = data.iloc[start_pos:end_pos+1]
                if len(cont_data) > 0:
                    high_price = cont_data['high'].max()
                    low_price = cont_data['low'].min()
                    price_range = high_price - low_price
                    range_percent = (price_range / low_price) * 100
                    duration = len(cont_data)
                    
                    contraction_nums.append(f'C{i+1}')
                    price_ranges.append(price_range)
                    durations.append(duration)
                    range_percents.append(range_percent)
        
        if price_ranges:
            # Create side-by-side bars
            x = np.arange(len(contraction_nums))
            width = 0.35
            
            # Price range bars
            bars1 = ax.bar(x - width/2, range_percents, width, label='Price Range %', 
                          color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'][:len(range_percents)], 
                          alpha=0.7)
            
            # Duration bars (scaled for visibility)
            scaled_durations = [d * max(range_percents) / max(durations) for d in durations]
            bars2 = ax.bar(x + width/2, scaled_durations, width, label='Duration (scaled)', 
                          color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'][:len(durations)], 
                          alpha=0.4)
            
            # Add value labels
            for i, (bar, val) in enumerate(zip(bars1, range_percents)):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                       f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')
            
            for i, (bar, val) in enumerate(zip(bars2, durations)):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                       f'{val}d', ha='center', va='bottom', fontweight='bold')
            
            ax.set_xlabel('Contraction', fontweight='bold')
            ax.set_ylabel('Percentage / Days', fontweight='bold')
            ax.set_title('VCP Rule: Each Bar Should Get SMALLER', fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(contraction_nums)
            ax.legend()
            ax.grid(True, alpha=0.3)
    
    def _plot_vcp_explanation(self, ax):
        """Show VCP explanation text"""
        
        ax.axis('off')  # Remove axes for text display
        
        explanation_text = """📚 VOLATILITY CONTRACTION PATTERN (VCP)

🎯 WHAT IS VOLATILITY CONTRACTION?
• Price pullbacks get PROGRESSIVELY SMALLER
• Each decline has less "range" than the previous
• Shows selling pressure is DIMINISHING
• Eventually leads to explosive breakout

📏 HOW TO MEASURE CONTRACTIONS:
1️⃣ Mark each pullback/correction period
2️⃣ Measure High-to-Low range in each
3️⃣ Calculate percentage decline
4️⃣ Verify each is SMALLER than previous

✅ IDEAL VCP PATTERN:
• C1: 15-20% decline over 3-4 weeks
• C2: 10-15% decline over 2-3 weeks  
• C3: 5-10% decline over 1-2 weeks
• C4: 2-5% decline over few days

📊 VOLUME REQUIREMENTS:
• Volume should DECREASE with each contraction
• Shows fewer sellers each time
• Confirms weakening selling pressure

🚀 BREAKOUT SIGNAL:
• When price breaks above resistance
• On INCREASED volume
• After 3+ tight contractions

⚠️ WHAT TO AVOID:
❌ Contractions getting WIDER (not tighter)
❌ Volume increasing during pullbacks
❌ Breaking below major support levels
❌ More than 6-7 contractions (exhausted)

💡 TRADING STRATEGY:
🎯 Entry: 2% above resistance breakout
🛑 Stop: 2% below recent support
📈 Target: 20-30% from entry point"""
        
        ax.text(0.05, 0.95, explanation_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', fontfamily='monospace',
               bbox=dict(boxstyle="round,pad=0.5", facecolor='lightcyan', alpha=0.9))
    
    def _format_educational_axis(self, ax, data):
        """Format x-axis for educational clarity"""
        
        ax.set_xlim(-0.5, len(data) - 0.5)
        
        # Fewer ticks for clarity
        trading_days = len(data)
        if trading_days <= 50:
            tick_interval = 5
        else:
            tick_interval = 10
        
        tick_positions = list(range(0, len(data), tick_interval))
        if tick_positions[-1] != len(data) - 1:
            tick_positions.append(len(data) - 1)
        
        tick_labels = [data.iloc[pos]['date'].strftime('%b %d') for pos in tick_positions]
        
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45)
        ax.grid(True, alpha=0.3, axis='x')

def main():
    """Create educational VCP charts"""
    
    print("📚 CREATING VCP EDUCATIONAL CHARTS")
    print("=" * 55)
    print("Purpose: Clearly explain what volatility contraction means")
    
    # Create educational charts for top VCP examples
    symbols = ['CIPLA', 'HDFCBANK', 'BAJAJFINSV']
    
    chart_creator = VCPEducationalChart()
    created_charts = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] Creating educational chart for {symbol}")
        print("-" * 50)
        
        chart_path = chart_creator.create_educational_vcp_chart(symbol)
        
        if chart_path:
            created_charts.append((symbol, chart_path))
            print(f"✅ SUCCESS: {chart_path}")
        else:
            print(f"❌ FAILED: No chart created")
    
    print(f"\n📚 VCP EDUCATIONAL CHARTS COMPLETE!")
    print(f"Successfully created {len(created_charts)}/{len(symbols)} educational charts")
    
    if created_charts:
        print(f"\n✅ EDUCATIONAL CHARTS CREATED:")
        for symbol, path in created_charts:
            print(f"   📚 {symbol:<12} → {path}")
        
        print(f"\n💡 EDUCATIONAL FEATURES:")
        print(f"   📏 Clear volatility measurements on each contraction")
        print(f"   📊 Bar chart showing progressive contraction sizing")
        print(f"   📚 Complete VCP explanation and trading rules")
        print(f"   🎯 Visual range measurements with percentage calculations")
        print(f"   📈 Volume dry-up analysis during contractions")

if __name__ == "__main__":
    main()