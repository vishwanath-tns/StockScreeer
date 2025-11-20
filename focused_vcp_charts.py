"""
VCP Pattern Focused Charts
=========================
Create charts showing only the periods when VCP patterns were detected
This allows zooming in to see exactly how the patterns look
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import date, timedelta
from volatility_patterns.data.data_service import DataService
from volatility_patterns.core.vcp_detector import VCPDetector
from volatility_patterns.analysis.vcp_scanner import VCPScanner
import json
import seaborn as sns

# Set clean style
plt.style.use('seaborn-v0_8')

class VCPPatternFocusedCharts:
    """
    Create focused charts showing only periods when VCP patterns were detected
    """
    
    def __init__(self):
        self.data_service = DataService()
        self.detector = VCPDetector()
        self.scanner = VCPScanner()
    
    def create_pattern_focused_chart(self, symbol: str, save_path: str = None):
        """Create a chart focused on the VCP pattern detection period"""
        
        print(f"🔍 Scanning {symbol} for VCP patterns...")
        
        # Use scanner to find patterns with longer lookback
        result = self.scanner.scan_single_stock(
            symbol=symbol,
            lookback_days=500,  # Look back further
            min_quality=25.0    # Lower threshold to find patterns
        )
        
        if not result.best_pattern:
            print(f"❌ No VCP pattern found in {symbol}")
            return None
        
        pattern = result.best_pattern
        print(f"✅ Found VCP pattern in {symbol} (Quality: {pattern.quality_score:.1f})")
        
        # Get focused time range around the pattern
        pattern_start = pattern.base_start_date
        pattern_end = pattern.base_end_date
        
        # Extend range for context (30 days before, 60 days after)
        chart_start = pattern_start - timedelta(days=30)
        chart_end = pattern_end + timedelta(days=60)
        
        print(f"📊 Creating focused chart for {symbol}")
        print(f"   Pattern Period: {pattern_start} to {pattern_end}")
        print(f"   Chart Range: {chart_start} to {chart_end}")
        
        # Get data for focused period
        data = self.data_service.get_ohlcv_data(symbol, chart_start, chart_end)
        if len(data) < 20:
            print(f"❌ Insufficient data for focused chart")
            return None
        
        # Create focused chart
        fig = self._create_focused_chart(data, pattern, symbol, chart_start, chart_end)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Focused chart saved: {save_path}")
            plt.close(fig)
        
        return save_path
    
    def _create_focused_chart(self, data, pattern, symbol, chart_start, chart_end):
        """Create the actual focused chart"""
        
        # Create subplot layout
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), height_ratios=[3, 1])
        
        # Plot 1: Price chart with detailed pattern annotations
        self._plot_focused_price_chart(ax1, data, pattern, symbol)
        
        # Plot 2: Volume chart
        self._plot_focused_volume_chart(ax2, data, pattern)
        
        # Add main title
        fig.suptitle(f'{symbol} - VCP Pattern Focused View (Quality: {pattern.quality_score:.1f})', 
                     fontsize=16, fontweight='bold', y=0.98)
        
        plt.tight_layout()
        return fig
    
    def _plot_focused_price_chart(self, ax, data, pattern, symbol):
        """Plot price chart with detailed VCP pattern annotations"""
        
        # Plot price line
        ax.plot(data.index, data['close'], linewidth=2.5, color='#2E86AB', label='Price', zorder=3)
        
        # Add moving averages
        ma10 = data['close'].rolling(10, min_periods=1).mean()
        ma20 = data['close'].rolling(20, min_periods=1).mean()
        ma50 = data['close'].rolling(50, min_periods=1).mean()
        
        ax.plot(data.index, ma10, '--', alpha=0.8, color='purple', linewidth=1, label='10-day MA')
        ax.plot(data.index, ma20, '--', alpha=0.8, color='orange', linewidth=1.5, label='20-day MA')
        ax.plot(data.index, ma50, '--', alpha=0.8, color='red', linewidth=1.5, label='50-day MA')
        
        # Highlight the VCP base period
        base_start = pattern.base_start_date
        base_end = pattern.base_end_date
        
        ax.axvspan(base_start, base_end, alpha=0.15, color='green', 
                  label='VCP Base Period', zorder=1)
        
        # Annotate each contraction in detail
        self._annotate_contractions_detailed(ax, data, pattern)
        
        # Mark key levels
        self._mark_key_levels(ax, data, pattern)
        
        # Add pattern information box
        self._add_pattern_info_box(ax, pattern)
        
        ax.set_ylabel('Price (₹)', fontsize=12, fontweight='bold')
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_title(f'VCP Pattern Detail - {len(pattern.contractions)} Contractions', 
                    fontsize=14, fontweight='bold')
    
    def _annotate_contractions_detailed(self, ax, data, pattern):
        """Add detailed annotations for each contraction"""
        
        # Get base data for reference
        base_data = data[(data.index >= pattern.base_start_date) & 
                        (data.index <= pattern.base_end_date)]
        base_high = base_data['high'].max()
        base_low = base_data['low'].min()
        
        for i, contraction in enumerate(pattern.contractions[:6]):  # Show up to 6 contractions
            # Highlight contraction period
            ax.axvspan(contraction.start_date, contraction.end_date, 
                      alpha=0.25, color=f'C{i}', linewidth=0, zorder=2)
            
            # Get contraction data
            cont_data = data[(data.index >= contraction.start_date) & 
                           (data.index <= contraction.end_date)]
            
            if len(cont_data) == 0:
                continue
            
            cont_high = cont_data['high'].max()
            cont_low = cont_data['low'].min()
            cont_range = cont_high - cont_low
            
            # Mark contraction number and stats
            mid_date = contraction.start_date + (contraction.end_date - contraction.start_date) / 2
            
            # Position annotation above the high
            y_pos = cont_high + (base_high - base_low) * 0.03
            
            annotation_text = f'C{i+1}\n{cont_range:.1f}₹\n{contraction.volatility_contraction:.1f}%'
            
            ax.annotate(annotation_text, 
                       xy=(mid_date, cont_high), 
                       xytext=(mid_date, y_pos),
                       fontsize=9, ha='center', fontweight='bold',
                       bbox=dict(boxstyle="round,pad=0.3", facecolor=f'C{i}', alpha=0.7),
                       arrowprops=dict(arrowstyle='->', color=f'C{i}', lw=1.5))
            
            # Mark the low point of each contraction
            ax.plot(cont_data.idxmin()['low'], cont_low, 'o', 
                   color=f'C{i}', markersize=8, markeredgecolor='white', 
                   markeredgewidth=2, zorder=4)
    
    def _mark_key_levels(self, ax, data, pattern):
        """Mark key support and resistance levels"""
        
        # Get base data
        base_data = data[(data.index >= pattern.base_start_date) & 
                        (data.index <= pattern.base_end_date)]
        
        # Resistance (base high)
        resistance = base_data['high'].max()
        ax.axhline(y=resistance, color='red', linestyle='-', linewidth=2.5, alpha=0.8,
                  label=f'Resistance: ₹{resistance:.1f}', zorder=3)
        
        # Support (base low)  
        support = base_data['low'].min()
        ax.axhline(y=support, color='green', linestyle='-', linewidth=2, alpha=0.8,
                  label=f'Support: ₹{support:.1f}', zorder=3)
        
        # Pivot point (average of last contraction)
        if pattern.contractions:
            last_cont = pattern.contractions[-1]
            last_cont_data = data[(data.index >= last_cont.start_date) & 
                                 (data.index <= last_cont.end_date)]
            if len(last_cont_data) > 0:
                pivot = (last_cont_data['high'].max() + last_cont_data['low'].min()) / 2
                ax.axhline(y=pivot, color='orange', linestyle=':', linewidth=2, alpha=0.8,
                          label=f'Pivot: ₹{pivot:.1f}', zorder=3)
        
        # Current price
        current_price = data['close'].iloc[-1]
        ax.axhline(y=current_price, color='purple', linestyle='--', linewidth=2, alpha=0.8,
                  label=f'Current: ₹{current_price:.1f}', zorder=3)
    
    def _add_pattern_info_box(self, ax, pattern):
        """Add detailed pattern information"""
        
        # Calculate pattern statistics
        total_days = (pattern.base_end_date - pattern.base_start_date).days
        avg_contraction = np.mean([c.volatility_contraction for c in pattern.contractions])
        
        info_text = f"""VCP Pattern Analysis
────────────────────
Quality Score: {pattern.quality_score:.1f}
Pattern Stage: {pattern.current_stage}
Base Duration: {total_days} days
Contractions: {len(pattern.contractions)}
Avg Contraction: {avg_contraction:.1f}%
Compression: {pattern.volatility_compression:.1f}x
Setup Complete: {'✅ Yes' if pattern.is_setup_complete else '❌ No'}"""
        
        ax.text(0.98, 0.98, info_text, transform=ax.transAxes, fontsize=10,
               bbox=dict(boxstyle="round,pad=0.5", facecolor='lightblue', alpha=0.9),
               verticalalignment='top', horizontalalignment='right',
               family='monospace')
    
    def _plot_focused_volume_chart(self, ax, data, pattern):
        """Plot volume chart with pattern periods highlighted"""
        
        # Volume bars
        colors = ['green' if close >= open_price else 'red' 
                 for close, open_price in zip(data['close'], data['open'])]
        
        bars = ax.bar(data.index, data['volume'], color=colors, alpha=0.6, width=0.8)
        
        # Volume moving averages
        vol_ma10 = data['volume'].rolling(10, min_periods=1).mean()
        vol_ma20 = data['volume'].rolling(20, min_periods=1).mean()
        
        ax.plot(data.index, vol_ma10, color='purple', linewidth=1.5, label='Vol MA(10)')
        ax.plot(data.index, vol_ma20, color='black', linewidth=2, label='Vol MA(20)')
        
        # Highlight contraction periods with low volume
        for i, contraction in enumerate(pattern.contractions[:6]):
            ax.axvspan(contraction.start_date, contraction.end_date, 
                      alpha=0.2, color=f'C{i}', zorder=1)
        
        # Mark average volume levels
        avg_volume = data['volume'].mean()
        ax.axhline(y=avg_volume, color='orange', linestyle='--', alpha=0.7,
                  label=f'Avg Volume: {avg_volume:,.0f}')
        
        ax.set_ylabel('Volume', fontsize=12, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_title('Volume Analysis - Lower volume during contractions', fontsize=12)
        
        # Format y-axis to show volume in readable format
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))


def create_focused_charts_for_detected_patterns():
    """Create focused charts for all detected VCP patterns"""
    
    print("🎯 CREATING FOCUSED CHARTS FOR DETECTED VCP PATTERNS")
    print("=" * 60)
    
    # Load detected patterns from previous analysis
    results_file = 'broader_universe_results/vcp_scan_results_20251116_155922.json'
    
    try:
        with open(results_file, 'r') as f:
            scan_results = json.load(f)
        
        # Get unique patterns with quality > 70
        all_patterns = scan_results['all_patterns']
        unique_patterns = {}
        
        for pattern in all_patterns:
            symbol = pattern['symbol']
            if (symbol not in unique_patterns or 
                pattern['quality_score'] > unique_patterns[symbol]['quality_score']):
                if pattern['quality_score'] >= 70:  # Only high-quality patterns
                    unique_patterns[symbol] = pattern
        
        print(f"Found {len(unique_patterns)} high-quality patterns to chart")
        
    except FileNotFoundError:
        print("❌ Previous scan results not found. Using top symbols...")
        # Fallback to known good symbols
        unique_patterns = {
            'HDFCBANK': {'quality_score': 94.2},
            'CIPLA': {'quality_score': 94.1},
            'BAJAJFINSV': {'quality_score': 93.4},
            'BIOCON': {'quality_score': 93.4},
            'BRITANNIA': {'quality_score': 93.4}
        }
    
    # Create focused charts
    chart_creator = VCPPatternFocusedCharts()
    successful_charts = []
    
    # Sort patterns by quality score
    sorted_patterns = sorted(unique_patterns.items(), 
                           key=lambda x: x[1]['quality_score'], 
                           reverse=True)
    
    for i, (symbol, pattern_info) in enumerate(sorted_patterns[:8], 1):  # Top 8 patterns
        print(f"\n[{i}/{min(8, len(sorted_patterns))}] Creating focused chart for {symbol}")
        print(f"   Quality Score: {pattern_info['quality_score']:.1f}")
        
        try:
            chart_path = f"charts/focused_vcp_{symbol}_Q{pattern_info['quality_score']:.0f}.png"
            
            result_path = chart_creator.create_pattern_focused_chart(
                symbol=symbol,
                save_path=chart_path
            )
            
            if result_path:
                successful_charts.append({
                    'symbol': symbol,
                    'quality': pattern_info['quality_score'],
                    'path': result_path
                })
                
        except Exception as e:
            print(f"❌ Failed to create focused chart for {symbol}: {e}")
    
    # Summary
    print(f"\n📊 FOCUSED CHART CREATION COMPLETE!")
    print(f"Successfully created {len(successful_charts)} focused charts")
    
    if successful_charts:
        print(f"\n✅ FOCUSED CHARTS CREATED:")
        for chart in successful_charts:
            print(f"   📈 {chart['symbol']:12} (Q: {chart['quality']:5.1f}) → {chart['path']}")
    
    print(f"\n💡 These charts show ONLY the periods when VCP patterns were detected!")
    print(f"   You can now zoom in and see exactly how the patterns look.")
    
    return successful_charts


if __name__ == "__main__":
    create_focused_charts_for_detected_patterns()