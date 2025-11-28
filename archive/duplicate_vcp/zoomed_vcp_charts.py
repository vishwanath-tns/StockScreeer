"""
VCP Pattern Zoomed Charts - Focused Time Range
==============================================
Create charts that zoom in ONLY on the VCP pattern formation period
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import date, timedelta
from volatility_patterns.data.data_service import DataService
from volatility_patterns.core.vcp_detector import VCPDetector
import seaborn as sns

# Set clean style
plt.style.use('seaborn-v0_8')

class VCPZoomedCharts:
    """
    Create zoomed charts showing ONLY the VCP pattern formation period
    """
    
    def __init__(self):
        self.data_service = DataService()
        self.detector = VCPDetector()
    
    def create_zoomed_vcp_chart(self, symbol: str, save_path: str = None):
        """Create a chart zoomed to just the VCP pattern period"""
        
        print(f"🔍 Creating zoomed VCP chart for {symbol}...")
        
        try:
            # First, get extended data to find patterns
            end_date = date.today()
            start_date = end_date - timedelta(days=540)  # 18 months to find patterns
            
            print(f"   Scanning {symbol} for patterns...")
            
            # Get full data for pattern detection
            full_data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
            if len(full_data) < 100:
                print(f"❌ Insufficient data for {symbol}")
                return None
            
            # Detect patterns
            patterns = self.detector.detect_vcp_patterns(full_data, symbol)
            if not patterns:
                print(f"❌ No VCP pattern found in {symbol}")
                return None
            
            # Get the best pattern
            best_pattern = max(patterns, key=lambda p: p.quality_score)
            print(f"✅ Found pattern (Quality: {best_pattern.quality_score:.1f})")
            
            # Now get FOCUSED data - just the pattern period + small buffer
            pattern_start = best_pattern.pattern_start
            pattern_end = best_pattern.pattern_end
            
            # Create focused timeframe (only 30 days before and 20 days after pattern)
            chart_start = pattern_start - timedelta(days=30)
            chart_end = pattern_end + timedelta(days=20)
            
            print(f"   Pattern period: {pattern_start} to {pattern_end}")
            print(f"   Chart focus: {chart_start} to {chart_end}")
            
            # Get ONLY the focused data
            focused_data = self.data_service.get_ohlcv_data(symbol, chart_start, chart_end)
            
            if len(focused_data) < 20:
                print(f"❌ Insufficient focused data")
                return None
            
            print(f"   Focused data points: {len(focused_data)}")
            
            # Create the zoomed chart
            fig = self._create_zoomed_chart(focused_data, best_pattern, symbol)
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"✅ Zoomed chart saved: {save_path}")
                plt.close(fig)
            
            return save_path
            
        except Exception as e:
            print(f"❌ Error creating zoomed chart for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_zoomed_chart(self, data, pattern, symbol):
        """Create the zoomed chart focusing only on pattern period"""
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), height_ratios=[3, 1])
        
        # Plot 1: Zoomed price chart
        self._plot_zoomed_price_chart(ax1, data, pattern, symbol)
        
        # Plot 2: Volume chart
        self._plot_zoomed_volume_chart(ax2, data, pattern)
        
        # Main title
        duration = (pattern.pattern_end - pattern.pattern_start).days
        fig.suptitle(f'{symbol} - VCP Pattern Zoomed View (Quality: {pattern.quality_score:.1f}, {duration} days)', 
                     fontsize=16, fontweight='bold', y=0.98)
        
        plt.tight_layout()
        return fig
    
    def _plot_zoomed_price_chart(self, ax, data, pattern, symbol):
        """Plot zoomed price chart with clear VCP annotations"""
        
        # Main price line (thicker for visibility)
        ax.plot(data['date'], data['close'], linewidth=3, color='#2E86AB', 
                label='Close Price', zorder=4)
        
        # Price range (high-low) for context
        ax.fill_between(data['date'], data['low'], data['high'], 
                       alpha=0.15, color='lightblue', label='Daily Range', zorder=1)
        
        # Moving averages (only relevant ones for this timeframe)
        if len(data) > 10:
            ma10 = data['close'].rolling(10, min_periods=1).mean()
            ax.plot(data['date'], ma10, '--', alpha=0.8, color='orange', linewidth=2, label='MA10')
        
        if len(data) > 20:
            ma20 = data['close'].rolling(20, min_periods=1).mean()
            ax.plot(data['date'], ma20, '--', alpha=0.8, color='red', linewidth=2, label='MA20')
        
        # Highlight the ENTIRE VCP base period
        ax.axvspan(pattern.pattern_start, pattern.pattern_end, 
                  alpha=0.2, color='green', label='VCP Base Period', zorder=2)
        
        # Mark each contraction clearly
        self._mark_contractions_zoomed(ax, data, pattern)
        
        # Mark key levels
        self._mark_key_levels_zoomed(ax, data, pattern)
        
        # Add focused pattern info
        self._add_zoomed_info_box(ax, pattern)
        
        # Formatting
        ax.set_ylabel('Price (₹)', fontsize=14, fontweight='bold')
        ax.legend(loc='upper left', fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.set_title(f'VCP Pattern Formation - {len(pattern.contractions)} Contractions', 
                    fontsize=14, fontweight='bold')
        
        # Format dates nicely
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.tick_params(axis='x', rotation=45)
    
    def _mark_contractions_zoomed(self, ax, data, pattern):
        """Mark contractions with clear visibility in zoomed view"""
        
        # Colors for different contractions
        colors = ['red', 'orange', 'purple', 'brown', 'pink', 'gray']
        
        for i, contraction in enumerate(pattern.contractions):
            if i >= 6:  # Limit to 6 contractions for clarity
                break
                
            color = colors[i % len(colors)]
            
            # Highlight the entire contraction period
            ax.axvspan(contraction.start_date, contraction.end_date, 
                      alpha=0.3, color=color, zorder=3)
            
            # Get contraction data - using date column, convert dates to pandas datetime
            start_dt = pd.to_datetime(contraction.start_date)
            end_dt = pd.to_datetime(contraction.end_date)
            cont_data = data[(data['date'] >= start_dt) & 
                           (data['date'] <= end_dt)]
            
            if len(cont_data) == 0:
                continue
            
            # Calculate contraction statistics
            cont_high = cont_data['high'].max()
            cont_low = cont_data['low'].min()
            cont_range_pct = ((cont_high - cont_low) / cont_low) * 100
            
            # Position for annotation (above the high)
            mid_date = contraction.start_date + (contraction.end_date - contraction.start_date) / 2
            y_offset = (data['high'].max() - data['low'].min()) * 0.05
            
            # Create detailed annotation
            annotation_text = f'C{i+1}\n{cont_range_pct:.1f}%\n{contraction.duration_days}d'
            
            ax.annotate(annotation_text, 
                       xy=(mid_date, cont_high), 
                       xytext=(mid_date, cont_high + y_offset),
                       fontsize=11, ha='center', fontweight='bold',
                       bbox=dict(boxstyle="round,pad=0.4", facecolor=color, alpha=0.9),
                       arrowprops=dict(arrowstyle='->', color=color, lw=2))
            
            # Mark the exact low point
            low_date = cont_data.idxmin()['low']
            ax.plot(low_date, cont_low, 'o', color=color, markersize=10, 
                   markeredgecolor='white', markeredgewidth=3, zorder=5,
                   label=f'C{i+1} Low' if i < 3 else "")  # Only label first 3
    
    def _mark_key_levels_zoomed(self, ax, data, pattern):
        """Mark key support/resistance levels for zoomed view"""
        
        # Get pattern data - convert dates to pandas datetime
        pattern_start_dt = pd.to_datetime(pattern.pattern_start)
        pattern_end_dt = pd.to_datetime(pattern.pattern_end)
        pattern_data = data[(data['date'] >= pattern_start_dt) & 
                           (data['date'] <= pattern_end_dt)]
        
        if len(pattern_data) > 0:
            # Resistance (pattern high)
            resistance = pattern_data['high'].max()
            ax.axhline(y=resistance, color='red', linestyle='-', linewidth=3, alpha=0.9,
                      label=f'Resistance: ₹{resistance:.1f}', zorder=4)
            
            # Support (pattern low)
            support = pattern_data['low'].min()
            ax.axhline(y=support, color='green', linestyle='-', linewidth=3, alpha=0.9,
                      label=f'Support: ₹{support:.1f}', zorder=4)
            
            # Add level labels on the right
            ax.text(data['date'].iloc[-1], resistance, f'  ₹{resistance:.1f}', 
                   va='center', ha='left', fontweight='bold', color='red', fontsize=12)
            ax.text(data['date'].iloc[-1], support, f'  ₹{support:.1f}', 
                   va='center', ha='left', fontweight='bold', color='green', fontsize=12)
        
        # Current price
        current_price = data['close'].iloc[-1]
        ax.axhline(y=current_price, color='purple', linestyle='--', linewidth=2, alpha=0.8,
                  label=f'Current: ₹{current_price:.1f}', zorder=4)
    
    def _add_zoomed_info_box(self, ax, pattern):
        """Add pattern information box for zoomed view"""
        
        # Calculate some additional stats
        total_days = (pattern.pattern_end - pattern.pattern_start).days
        avg_contraction_days = np.mean([c.duration_days for c in pattern.contractions]) if pattern.contractions else 0
        
        info_text = f"""VCP Pattern Analysis
{'━' * 22}
Quality Score: {pattern.quality_score:.1f}/100
Stage: {pattern.current_stage}
Base Duration: {total_days} days
Contractions: {len(pattern.contractions)}
Avg Contraction: {avg_contraction_days:.0f} days
Volatility Compression: {pattern.volatility_compression:.1f}x
Setup Complete: {'✅' if pattern.is_setup_complete else '❌'}"""
        
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=11,
               bbox=dict(boxstyle="round,pad=0.5", facecolor='lightyellow', alpha=0.95),
               verticalalignment='top', horizontalalignment='left',
               family='monospace', fontweight='bold')
    
    def _plot_zoomed_volume_chart(self, ax, data, pattern):
        """Plot volume chart for zoomed timeframe"""
        
        # Volume bars
        colors = ['green' if close >= open_price else 'red' 
                 for close, open_price in zip(data['close'], data['open'])]
        
        ax.bar(data['date'], data['volume'], color=colors, alpha=0.7, width=0.8)
        
        # Volume moving average (shorter period for zoomed view)
        if len(data) > 5:
            vol_ma = data['volume'].rolling(5, min_periods=1).mean()
            ax.plot(data['date'], vol_ma, color='black', linewidth=3, label='Vol MA(5)')
        
        # Highlight contraction periods
        for i, contraction in enumerate(pattern.contractions[:6]):
            color = ['red', 'orange', 'purple', 'brown', 'pink', 'gray'][i % 6]
            ax.axvspan(contraction.start_date, contraction.end_date, 
                      alpha=0.2, color=color, zorder=1)
        
        # Mark average volume
        avg_volume = data['volume'].mean()
        ax.axhline(y=avg_volume, color='blue', linestyle='--', alpha=0.8, linewidth=2,
                  label=f'Avg: {avg_volume:,.0f}')
        
        ax.set_ylabel('Volume', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date', fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.set_title('Volume Profile (Should decline during contractions)', fontsize=12)
        
        # Format volume axis
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))
        ax.tick_params(axis='x', rotation=45)


def create_zoomed_vcp_charts():
    """Create zoomed VCP charts for top patterns"""
    
    print("🔍 CREATING ZOOMED VCP PATTERN CHARTS")
    print("=" * 50)
    print("These charts focus ONLY on the VCP pattern formation period")
    
    # Test symbols
    test_symbols = [
        'HDFCBANK', 'CIPLA', 'BAJAJFINSV', 'BIOCON', 
        'BRITANNIA', 'KOTAKBANK', 'TITAN'
    ]
    
    chart_creator = VCPZoomedCharts()
    successful_charts = []
    
    for i, symbol in enumerate(test_symbols, 1):
        print(f"\n[{i}/{len(test_symbols)}] Creating zoomed chart for {symbol}")
        print("-" * 30)
        
        try:
            chart_path = f"charts/zoomed_vcp_{symbol}.png"
            
            result_path = chart_creator.create_zoomed_vcp_chart(
                symbol=symbol,
                save_path=chart_path
            )
            
            if result_path:
                successful_charts.append({
                    'symbol': symbol,
                    'path': result_path
                })
                print(f"✅ SUCCESS: {result_path}")
            else:
                print(f"❌ FAILED: No chart created")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    # Summary
    print(f"\n📊 ZOOMED CHART CREATION COMPLETE!")
    print(f"Successfully created {len(successful_charts)}/{len(test_symbols)} zoomed charts")
    
    if successful_charts:
        print(f"\n✅ ZOOMED CHARTS CREATED:")
        for chart in successful_charts:
            print(f"   🔍 {chart['symbol']:12} → {chart['path']}")
    
    print(f"\n💡 KEY FEATURES OF ZOOMED CHARTS:")
    print(f"   • Shows ONLY the VCP pattern formation period")
    print(f"   • Clear contraction markings (C1, C2, C3...)")
    print(f"   • Visible support/resistance levels")
    print(f"   • Focused timeframe for pattern analysis")
    print(f"   • Volume analysis during contractions")
    
    return successful_charts


if __name__ == "__main__":
    create_zoomed_vcp_charts()