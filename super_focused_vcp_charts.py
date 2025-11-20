"""
Super Focused VCP Charts - Show Only Actual Contraction Periods
================================================================
Create charts showing ONLY the periods when actual contractions are happening
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

class SuperFocusedVCPCharts:
    """Create charts showing only actual contraction periods with small buffers"""
    
    def __init__(self):
        self.data_service = DataService()
        self.detector = VCPDetector()
        
    def create_super_focused_chart(self, symbol):
        """Create a chart focusing only on actual contraction periods"""
        
        try:
            print(f"🔍 Creating super focused VCP chart for {symbol}...")
            
            # Get full year of data for pattern detection
            end_date = date.today()
            start_date = date(end_date.year - 1, 1, 1)
            
            print(f"   Scanning {symbol} for patterns...")
            data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
            
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
            
            # Calculate actual contraction timeframe
            if not best_pattern.contractions:
                print(f"   ❌ No contractions in pattern")
                return None
            
            # Get the actual period where contractions happen
            first_cont_start = min(c.start_date for c in best_pattern.contractions)
            last_cont_end = max(c.end_date for c in best_pattern.contractions)
            
            # Add small buffer (10 trading days before/after actual contractions)
            buffer_days = 14  # 2 weeks buffer
            focus_start = first_cont_start - timedelta(days=buffer_days)
            focus_end = last_cont_end + timedelta(days=buffer_days)
            
            actual_duration = (last_cont_end - first_cont_start).days
            total_focus = (focus_end - focus_start).days
            
            print(f"   Contractions span: {first_cont_start} to {last_cont_end} ({actual_duration} days)")
            print(f"   Chart focus: {focus_start} to {focus_end} ({total_focus} days)")
            
            # Get focused data
            focused_data = self.data_service.get_ohlcv_data(symbol, focus_start, focus_end)
            print(f"   Focused data points: {len(focused_data)}")
            
            # Create chart
            fig = self._create_super_focused_chart(focused_data, best_pattern, symbol, 
                                                 first_cont_start, last_cont_end)
            
            # Save chart
            save_path = f"charts/super_focused_{symbol}.png"
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Super focused chart saved: {save_path}")
            return save_path
            
        except Exception as e:
            print(f"❌ Error creating super focused chart for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_super_focused_chart(self, data, pattern, symbol, cont_start, cont_end):
        """Create the actual super focused chart"""
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), 
                                      gridspec_kw={'height_ratios': [3, 1]})
        
        # Calculate stats
        actual_days = (cont_end - cont_start).days
        
        # Main title
        fig.suptitle(f'{symbol} - VCP Contractions Only (Quality: {pattern.quality_score:.1f}, {actual_days} days)', 
                    fontsize=18, fontweight='bold')
        
        # Plot price data
        self._plot_super_focused_price(ax1, data, pattern, symbol, cont_start, cont_end)
        
        # Plot volume
        self._plot_super_focused_volume(ax2, data, pattern)
        
        # Format dates on both axes
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        return fig
    
    def _plot_super_focused_price(self, ax, data, pattern, symbol, cont_start, cont_end):
        """Plot super focused price chart"""
        
        # Main price line
        ax.plot(data['date'], data['close'], linewidth=2, color='#2E86AB', 
                label='Close Price', zorder=5)
        
        # Price range
        ax.fill_between(data['date'], data['low'], data['high'], 
                       alpha=0.15, color='lightblue', label='Daily Range', zorder=1)
        
        # Mark the actual contraction period
        ax.axvspan(cont_start, cont_end, alpha=0.2, color='orange', 
                  label='Active Contraction Period', zorder=2)
        
        # Mark individual contractions with different colors
        colors = ['red', 'purple', 'brown', 'pink', 'gray', 'olive']
        
        for i, contraction in enumerate(pattern.contractions):
            if i >= 6:  # Limit colors
                color = colors[i % len(colors)]
            else:
                color = colors[i]
                
            # Highlight contraction period
            ax.axvspan(contraction.start_date, contraction.end_date, 
                      alpha=0.4, color=color, zorder=3)
            
            # Add contraction label
            mid_date = contraction.start_date + (contraction.end_date - contraction.start_date) / 2
            ax.text(mid_date, data['close'].max() * 0.98, f'C{i+1}', 
                   ha='center', va='top', fontweight='bold', fontsize=10,
                   bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.7))
        
        # Support and resistance
        pattern_data = data[(data['date'] >= pd.to_datetime(pattern.pattern_start)) & 
                           (data['date'] <= pd.to_datetime(pattern.pattern_end))]
        
        if len(pattern_data) > 0:
            resistance = pattern_data['high'].max()
            support = pattern_data['low'].min()
            
            ax.axhline(y=resistance, color='red', linestyle='--', linewidth=2, 
                      alpha=0.8, label=f'Resistance: ₹{resistance:.1f}')
            ax.axhline(y=support, color='green', linestyle='--', linewidth=2, 
                      alpha=0.8, label=f'Support: ₹{support:.1f}')
        
        # Current price
        current_price = data['close'].iloc[-1]
        ax.axhline(y=current_price, color='purple', linestyle='-.', linewidth=2,
                  label=f'Current: ₹{current_price:.1f}')
        
        # Add pattern info box
        info_text = f"""VCP Analysis:
Quality Score: {pattern.quality_score:.1f}/100
Contractions: {len(pattern.contractions)}
Active Period: {(cont_end - cont_start).days} days"""
        
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle="round,pad=0.5", 
                facecolor='lightyellow', alpha=0.8))
        
        ax.set_ylabel('Price (₹)', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_title('Price Action During Contraction Periods', fontsize=14, fontweight='bold')
    
    def _plot_super_focused_volume(self, ax, data, pattern):
        """Plot volume with contraction highlights"""
        
        # Volume bars
        colors = ['green' if close >= open_price else 'red' 
                 for close, open_price in zip(data['close'], data['open'])]
        
        ax.bar(data['date'], data['volume'], color=colors, alpha=0.7, width=0.8)
        
        # Volume moving average
        if len(data) > 5:
            vol_ma = data['volume'].rolling(5, min_periods=1).mean()
            ax.plot(data['date'], vol_ma, color='black', linewidth=2, label='Vol MA(5)')
        
        # Mark contractions on volume
        for i, contraction in enumerate(pattern.contractions):
            colors_vol = ['red', 'purple', 'brown', 'pink', 'gray', 'olive']
            color = colors_vol[i % len(colors_vol)]
            
            ax.axvspan(contraction.start_date, contraction.end_date, 
                      alpha=0.3, color=color, zorder=3)
        
        ax.set_ylabel('Volume', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_title('Volume During Contractions (Should Decline)', fontsize=12, fontweight='bold')

def main():
    """Create super focused VCP charts for top stocks"""
    
    print("🎯 CREATING SUPER FOCUSED VCP CHARTS")
    print("=" * 50)
    print("These charts show ONLY the actual contraction periods")
    
    # Top VCP stocks
    symbols = ['HDFCBANK', 'CIPLA', 'BAJAJFINSV', 'BIOCON', 'BRITANNIA']
    
    chart_creator = SuperFocusedVCPCharts()
    
    created_charts = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] Creating super focused chart for {symbol}")
        print("-" * 40)
        
        chart_path = chart_creator.create_super_focused_chart(symbol)
        
        if chart_path:
            created_charts.append((symbol, chart_path))
            print(f"✅ SUCCESS: {chart_path}")
        else:
            print(f"❌ FAILED: No chart created")
    
    # Summary
    print(f"\n📊 SUPER FOCUSED CHART CREATION COMPLETE!")
    print(f"Successfully created {len(created_charts)}/{len(symbols)} charts")
    
    if created_charts:
        print(f"\n✅ SUPER FOCUSED CHARTS CREATED:")
        for symbol, path in created_charts:
            print(f"   🎯 {symbol:<12} → {path}")
        
        print(f"\n💡 KEY FEATURES OF SUPER FOCUSED CHARTS:")
        print(f"   • Shows ONLY actual contraction periods")
        print(f"   • Small buffer around contractions for context")
        print(f"   • Clear individual contraction markings")
        print(f"   • No empty periods between contractions")
        print(f"   • Focused timeline for pattern analysis")

if __name__ == "__main__":
    main()