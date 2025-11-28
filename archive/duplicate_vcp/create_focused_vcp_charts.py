"""
VCP Pattern Focused Charts - Fixed Version
==========================================
Create detailed charts showing only periods when VCP patterns were detected
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
    
    def create_pattern_focused_chart(self, symbol: str, save_path: str = None):
        """Create a chart focused on the VCP pattern detection period"""
        
        print(f"🔍 Creating focused chart for {symbol}...")
        
        try:
            # Get extended data (18 months)
            end_date = date.today()
            start_date = end_date - timedelta(days=540)  # ~18 months
            
            # Fetch data
            data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
            if len(data) < 100:
                print(f"❌ Insufficient data for {symbol}")
                return None
            
            # Detect patterns
            patterns = self.detector.detect_vcp_patterns(data, symbol)
            if not patterns:
                print(f"❌ No VCP pattern found in {symbol}")
                return None
            
            # Get best pattern
            best_pattern = max(patterns, key=lambda p: p.quality_score)
            print(f"✅ Found pattern in {symbol} (Quality: {best_pattern.quality_score:.1f})")
            
            # Create focused time range around the pattern
            pattern_start = best_pattern.pattern_start
            pattern_end = best_pattern.pattern_end
            
            # Extend range for context (45 days before, 30 days after)
            chart_start = pattern_start - timedelta(days=45)
            chart_end = min(pattern_end + timedelta(days=30), end_date)
            
            # Filter data to focused range
            focused_data = data[(data.index >= chart_start) & (data.index <= chart_end)]
            
            if len(focused_data) < 20:
                print(f"❌ Insufficient data for focused chart")
                return None
            
            print(f"📊 Pattern period: {pattern_start} to {pattern_end}")
            print(f"   Chart range: {chart_start} to {chart_end}")
            print(f"   Data points: {len(focused_data)}")
            
            # Create the chart
            fig = self._create_focused_chart(focused_data, best_pattern, symbol)
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"✅ Focused chart saved: {save_path}")
                plt.close(fig)
            
            return save_path
            
        except Exception as e:
            print(f"❌ Error creating chart for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_focused_chart(self, data, pattern, symbol):
        """Create the detailed focused chart"""
        
        # Create figure with subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), height_ratios=[3, 1, 1])
        
        # Plot 1: Price chart with detailed annotations
        self._plot_detailed_price_chart(ax1, data, pattern, symbol)
        
        # Plot 2: Volume chart
        self._plot_volume_chart(ax2, data, pattern)
        
        # Plot 3: Technical indicators
        self._plot_technical_indicators(ax3, data, pattern)
        
        # Add main title
        fig.suptitle(f'{symbol} - VCP Pattern Focused Analysis (Quality: {pattern.quality_score:.1f})', 
                     fontsize=16, fontweight='bold', y=0.98)
        
        plt.tight_layout()
        return fig
    
    def _plot_detailed_price_chart(self, ax, data, pattern, symbol):
        """Plot detailed price chart with VCP annotations"""
        
        # Main price line
        ax.plot(data.index, data['close'], linewidth=2.5, color='#2E86AB', 
                label='Close Price', zorder=3)
        
        # Add candlestick-like high/low lines for context
        ax.fill_between(data.index, data['low'], data['high'], 
                       alpha=0.2, color='lightblue', label='Price Range')
        
        # Moving averages for trend context
        ma10 = data['close'].rolling(10, min_periods=1).mean()
        ma20 = data['close'].rolling(20, min_periods=1).mean()
        ma50 = data['close'].rolling(50, min_periods=1).mean()
        
        ax.plot(data.index, ma10, '--', alpha=0.8, color='purple', linewidth=1, label='MA10')
        ax.plot(data.index, ma20, '--', alpha=0.8, color='orange', linewidth=1.5, label='MA20')
        ax.plot(data.index, ma50, '--', alpha=0.8, color='red', linewidth=2, label='MA50')
        
        # Highlight the VCP base period
        ax.axvspan(pattern.pattern_start, pattern.pattern_end, 
                  alpha=0.15, color='green', label='VCP Base Period', zorder=1)
        
        # Annotate each contraction with details
        self._annotate_contractions(ax, data, pattern)
        
        # Mark key levels
        self._mark_support_resistance(ax, data, pattern)
        
        # Add pattern information box
        self._add_pattern_info_box(ax, pattern)
        
        ax.set_ylabel('Price (₹)', fontsize=12, fontweight='bold')
        ax.legend(loc='upper left', fontsize=10, ncol=2)
        ax.grid(True, alpha=0.3)
        ax.set_title(f'VCP Pattern Detail - {len(pattern.contractions)} Contractions', 
                    fontsize=14, fontweight='bold')
    
    def _annotate_contractions(self, ax, data, pattern):
        """Add detailed annotations for each contraction"""
        
        colors = ['red', 'orange', 'brown', 'purple', 'pink', 'gray']
        
        for i, contraction in enumerate(pattern.contractions[:6]):  # Show max 6
            color = colors[i % len(colors)]
            
            # Highlight contraction period
            ax.axvspan(contraction.start_date, contraction.end_date, 
                      alpha=0.25, color=color, zorder=2)
            
            # Get contraction price data
            cont_data = data[(data.index >= contraction.start_date) & 
                           (data.index <= contraction.end_date)]
            
            if len(cont_data) == 0:
                continue
            
            # Calculate statistics
            cont_high = cont_data['high'].max()
            cont_low = cont_data['low'].min()
            cont_range = ((cont_high - cont_low) / cont_low) * 100
            
            # Find position for annotation
            mid_date = contraction.start_date + (contraction.end_date - contraction.start_date) / 2
            y_pos = cont_high * 1.02
            
            # Create annotation
            annotation_text = f'C{i+1}\nRange: {cont_range:.1f}%\nDays: {contraction.duration_days}'
            
            ax.annotate(annotation_text, 
                       xy=(mid_date, cont_high), 
                       xytext=(mid_date, y_pos),
                       fontsize=9, ha='center', fontweight='bold',
                       bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.8),
                       arrowprops=dict(arrowstyle='->', color=color, lw=1.5))
            
            # Mark the low point
            low_date = cont_data.idxmin()['low']
            ax.plot(low_date, cont_low, 'o', color=color, markersize=8, 
                   markeredgecolor='white', markeredgewidth=2, zorder=4)
    
    def _mark_support_resistance(self, ax, data, pattern):
        """Mark key support and resistance levels"""
        
        # Pattern high (resistance)
        pattern_data = data[(data.index >= pattern.pattern_start) & 
                           (data.index <= pattern.pattern_end)]
        
        if len(pattern_data) > 0:
            resistance = pattern_data['high'].max()
            support = pattern_data['low'].min()
            
            ax.axhline(y=resistance, color='red', linestyle='-', linewidth=2.5, alpha=0.8,
                      label=f'Resistance: ₹{resistance:.1f}', zorder=3)
            
            ax.axhline(y=support, color='green', linestyle='-', linewidth=2, alpha=0.8,
                      label=f'Support: ₹{support:.1f}', zorder=3)
        
        # Current price
        current_price = data['close'].iloc[-1]
        ax.axhline(y=current_price, color='purple', linestyle='--', linewidth=2, alpha=0.8,
                  label=f'Current: ₹{current_price:.1f}', zorder=3)
        
        # Breakout level
        if hasattr(pattern, 'breakout_level') and pattern.breakout_level:
            ax.axhline(y=pattern.breakout_level, color='orange', linestyle=':', linewidth=2, alpha=0.8,
                      label=f'Breakout: ₹{pattern.breakout_level:.1f}', zorder=3)
    
    def _add_pattern_info_box(self, ax, pattern):
        """Add comprehensive pattern information"""
        
        info_text = f"""VCP Pattern Analysis
{'─'*20}
Quality Score: {pattern.quality_score:.1f}
Pattern Stage: {pattern.current_stage}
Base Duration: {pattern.base_duration} days
Contractions: {len(pattern.contractions)}
Volatility Compression: {pattern.volatility_compression:.1f}x
Volume Compression: {pattern.volume_compression:.1f}x
Setup Complete: {'✅ Yes' if pattern.is_setup_complete else '❌ No'}
Total Decline: {pattern.total_decline:.1f}%"""
        
        ax.text(0.98, 0.98, info_text, transform=ax.transAxes, fontsize=10,
               bbox=dict(boxstyle="round,pad=0.5", facecolor='lightblue', alpha=0.9),
               verticalalignment='top', horizontalalignment='right',
               family='monospace')
    
    def _plot_volume_chart(self, ax, data, pattern):
        """Plot volume with pattern highlighting"""
        
        # Volume bars with colors
        colors = ['green' if close >= open_price else 'red' 
                 for close, open_price in zip(data['close'], data['open'])]
        
        ax.bar(data.index, data['volume'], color=colors, alpha=0.6, width=0.8)
        
        # Volume moving averages
        vol_ma10 = data['volume'].rolling(10, min_periods=1).mean()
        vol_ma20 = data['volume'].rolling(20, min_periods=1).mean()
        
        ax.plot(data.index, vol_ma10, color='purple', linewidth=1.5, label='Vol MA10')
        ax.plot(data.index, vol_ma20, color='black', linewidth=2, label='Vol MA20')
        
        # Highlight contraction periods
        for i, contraction in enumerate(pattern.contractions[:6]):
            ax.axvspan(contraction.start_date, contraction.end_date, 
                      alpha=0.15, color=f'C{i}', zorder=1)
        
        ax.set_ylabel('Volume', fontsize=12, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_title('Volume Profile (Should decrease during contractions)', fontsize=12)
        
        # Format y-axis
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))
    
    def _plot_technical_indicators(self, ax, data, pattern):
        """Plot technical indicators for additional context"""
        
        # Calculate RSI
        rsi = self._calculate_rsi(data['close'], period=14)
        
        ax.plot(data.index, rsi, color='purple', linewidth=2, label='RSI(14)')
        
        # RSI levels
        ax.axhline(y=70, color='red', linestyle='--', alpha=0.7, label='Overbought (70)')
        ax.axhline(y=30, color='green', linestyle='--', alpha=0.7, label='Oversold (30)')
        ax.axhline(y=50, color='gray', linestyle='-', alpha=0.5, label='Neutral (50)')
        
        # Highlight pattern period
        ax.axvspan(pattern.pattern_start, pattern.pattern_end, alpha=0.1, color='green')
        
        ax.set_ylabel('RSI', fontsize=12, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_title('Relative Strength Index', fontsize=12)
        ax.set_ylim(0, 100)
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi


def create_focused_charts_for_top_patterns():
    """Create focused charts for top VCP patterns"""
    
    print("🎯 CREATING FOCUSED CHARTS FOR TOP VCP PATTERNS")
    print("=" * 60)
    
    # Top symbols from our analysis
    top_symbols = [
        ('HDFCBANK', 94.2),
        ('CIPLA', 94.1), 
        ('BAJAJFINSV', 93.4),
        ('BIOCON', 93.4),
        ('BRITANNIA', 93.4),
        ('KOTAKBANK', 93.3),
        ('TITAN', 91.2),
        ('SBIN', 90.8)
    ]
    
    chart_creator = VCPPatternFocusedCharts()
    successful_charts = []
    
    for i, (symbol, quality) in enumerate(top_symbols, 1):
        print(f"\n[{i}/{len(top_symbols)}] Creating focused chart for {symbol}")
        print(f"   Expected Quality: {quality:.1f}")
        print("-" * 40)
        
        try:
            chart_path = f"charts/focused_vcp_{symbol}_detailed.png"
            
            result_path = chart_creator.create_pattern_focused_chart(
                symbol=symbol,
                save_path=chart_path
            )
            
            if result_path:
                successful_charts.append({
                    'symbol': symbol,
                    'expected_quality': quality,
                    'path': result_path
                })
                
        except Exception as e:
            print(f"❌ Failed for {symbol}: {e}")
    
    # Summary
    print(f"\n📊 FOCUSED CHART CREATION COMPLETE!")
    print(f"Successfully created {len(successful_charts)}/{len(top_symbols)} focused charts")
    
    if successful_charts:
        print(f"\n✅ FOCUSED CHARTS CREATED:")
        for chart in successful_charts:
            print(f"   📈 {chart['symbol']:12} → {chart['path']}")
    
    print(f"\n💡 These charts show ONLY the periods when VCP patterns were detected!")
    print(f"   Each chart zooms in on the exact pattern formation period.")
    print(f"   Look for decreasing volatility in successive contractions (C1, C2, C3...).")
    
    return successful_charts


if __name__ == "__main__":
    create_focused_charts_for_top_patterns()