"""
Ultra Focused VCP Charts - Show Recent Significant Contractions Only
====================================================================
Create charts showing only the last 3-6 months of the most recent, significant contractions
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

class UltraFocusedVCPCharts:
    """Create charts showing only recent significant contractions (last 3-6 months)"""
    
    def __init__(self):
        self.data_service = DataService()
        self.detector = VCPDetector()
        
    def create_ultra_focused_chart(self, symbol):
        """Create a chart focusing only on recent significant contractions"""
        
        try:
            print(f"🎯 Creating ultra focused VCP chart for {symbol}...")
            
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
            
            # Focus on recent contractions only (last 6 months)
            cutoff_date = date.today() - timedelta(days=180)  # 6 months back
            recent_contractions = [
                c for c in best_pattern.contractions 
                if c.end_date >= cutoff_date
            ]
            
            if not recent_contractions:
                # If no recent contractions, take the last 5 contractions
                recent_contractions = best_pattern.contractions[-5:] if len(best_pattern.contractions) > 5 else best_pattern.contractions
            
            if not recent_contractions:
                print(f"   ❌ No recent contractions found")
                return None
            
            # Get timeframe for recent contractions
            first_recent = min(c.start_date for c in recent_contractions)
            last_recent = max(c.end_date for c in recent_contractions)
            
            # Add reasonable buffer (3 weeks before/after)
            buffer_days = 21
            focus_start = first_recent - timedelta(days=buffer_days)
            focus_end = last_recent + timedelta(days=buffer_days)
            
            # Ensure we don't go beyond available data
            focus_start = max(focus_start, data['date'].min().date())
            focus_end = min(focus_end, data['date'].max().date())
            
            duration = (focus_end - focus_start).days
            
            print(f"   Recent contractions: {len(recent_contractions)} found")
            print(f"   Timeframe: {first_recent} to {last_recent}")
            print(f"   Chart focus: {focus_start} to {focus_end} ({duration} days)")
            
            # Get focused data
            focused_data = self.data_service.get_ohlcv_data(symbol, focus_start, focus_end)
            print(f"   Focused data points: {len(focused_data)}")
            
            # Create chart
            fig = self._create_ultra_focused_chart(focused_data, best_pattern, recent_contractions, 
                                                 symbol, first_recent, last_recent)
            
            # Save chart
            save_path = f"charts/ultra_focused_{symbol}.png"
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Ultra focused chart saved: {save_path}")
            return save_path
            
        except Exception as e:
            print(f"❌ Error creating ultra focused chart for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_ultra_focused_chart(self, data, full_pattern, recent_contractions, 
                                  symbol, cont_start, cont_end):
        """Create the ultra focused chart"""
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 10), 
                                      gridspec_kw={'height_ratios': [3, 1]})
        
        # Calculate stats
        duration = (cont_end - cont_start).days
        
        # Main title
        fig.suptitle(f'{symbol} - Recent VCP Contractions (Quality: {full_pattern.quality_score:.1f}, {duration} days)', 
                    fontsize=16, fontweight='bold')
        
        # Plot price data
        self._plot_ultra_focused_price(ax1, data, full_pattern, recent_contractions, 
                                     symbol, cont_start, cont_end)
        
        # Plot volume
        self._plot_ultra_focused_volume(ax2, data, recent_contractions)
        
        # Format dates
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            # Adjust locator based on timeframe
            if duration <= 90:  # 3 months or less
                ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
            else:
                ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        return fig
    
    def _plot_ultra_focused_price(self, ax, data, full_pattern, recent_contractions, 
                                symbol, cont_start, cont_end):
        """Plot ultra focused price chart"""
        
        # Main price line (thicker for clarity)
        ax.plot(data['date'], data['close'], linewidth=2.5, color='#1f77b4', 
                label='Close Price', zorder=5)
        
        # Price range with subtle fill
        ax.fill_between(data['date'], data['low'], data['high'], 
                       alpha=0.1, color='lightblue', zorder=1)
        
        # Mark recent contractions with distinct colors
        contraction_colors = ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
        
        for i, contraction in enumerate(recent_contractions):
            color = contraction_colors[i % len(contraction_colors)]
            
            # Highlight contraction period
            ax.axvspan(contraction.start_date, contraction.end_date, 
                      alpha=0.3, color=color, zorder=3)
            
            # Calculate contraction stats
            cont_data = data[(data['date'] >= pd.to_datetime(contraction.start_date)) & 
                           (data['date'] <= pd.to_datetime(contraction.end_date))]
            
            if len(cont_data) > 0:
                price_range = ((cont_data['high'].max() - cont_data['low'].min()) / 
                             cont_data['low'].min()) * 100
                
                # Add contraction label with stats
                mid_date = contraction.start_date + (contraction.end_date - contraction.start_date) / 2
                duration = (contraction.end_date - contraction.start_date).days
                
                label_text = f'C{i+1}\n{duration}d\n{price_range:.1f}%'
                
                ax.text(mid_date, data['close'].max() * 0.985, label_text, 
                       ha='center', va='top', fontweight='bold', fontsize=9,
                       bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.8))
        
        # Key price levels
        recent_data = data[(data['date'] >= pd.to_datetime(cont_start)) & 
                          (data['date'] <= pd.to_datetime(cont_end))]
        
        if len(recent_data) > 0:
            resistance = recent_data['high'].max()
            support = recent_data['low'].min()
            
            ax.axhline(y=resistance, color='red', linestyle='--', linewidth=2, 
                      alpha=0.7, label=f'Recent High: ₹{resistance:.0f}')
            ax.axhline(y=support, color='green', linestyle='--', linewidth=2, 
                      alpha=0.7, label=f'Recent Low: ₹{support:.0f}')
        
        # Current price
        current_price = data['close'].iloc[-1]
        ax.axhline(y=current_price, color='purple', linestyle='-.', linewidth=2,
                  alpha=0.8, label=f'Current: ₹{current_price:.0f}')
        
        # Moving averages for context
        if len(data) > 20:
            ma20 = data['close'].rolling(20, min_periods=1).mean()
            ax.plot(data['date'], ma20, '--', alpha=0.7, color='orange', 
                   linewidth=1.5, label='MA20')
        
        # Info box
        info_text = f"""Pattern Analysis:
Quality: {full_pattern.quality_score:.1f}/100
Recent Contractions: {len(recent_contractions)}
Total Contractions: {len(full_pattern.contractions)}
Timeframe: {(cont_end - cont_start).days} days"""
        
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle="round,pad=0.4", 
                facecolor='lightyellow', alpha=0.9))
        
        ax.set_ylabel('Price (₹)', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_title('Recent VCP Contraction Analysis', fontsize=14, fontweight='bold')
    
    def _plot_ultra_focused_volume(self, ax, data, recent_contractions):
        """Plot volume with recent contraction highlights"""
        
        # Volume bars with color coding
        colors = ['darkgreen' if close >= open_price else 'darkred' 
                 for close, open_price in zip(data['close'], data['open'])]
        
        bars = ax.bar(data['date'], data['volume'], color=colors, alpha=0.6, width=0.8)
        
        # Volume moving average
        if len(data) > 10:
            vol_ma = data['volume'].rolling(10, min_periods=1).mean()
            ax.plot(data['date'], vol_ma, color='black', linewidth=2.5, 
                   label='Vol MA(10)', alpha=0.8)
        
        # Average volume line
        avg_volume = data['volume'].mean()
        ax.axhline(y=avg_volume, color='blue', linestyle=':', linewidth=2,
                  alpha=0.7, label=f'Avg Volume: {avg_volume:,.0f}')
        
        # Highlight contraction periods on volume
        contraction_colors = ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
        
        for i, contraction in enumerate(recent_contractions):
            color = contraction_colors[i % len(contraction_colors)]
            ax.axvspan(contraction.start_date, contraction.end_date, 
                      alpha=0.25, color=color, zorder=3)
        
        # Format volume numbers
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
        
        ax.set_ylabel('Volume', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_title('Volume During Contractions (Should Show Declining Trend)', fontsize=12, fontweight='bold')

def main():
    """Create ultra focused VCP charts"""
    
    print("🎯 CREATING ULTRA FOCUSED VCP CHARTS")
    print("=" * 55)
    print("These charts show ONLY recent significant contractions")
    
    # Test with CIPLA first to see if this resolves the issue
    symbols = ['CIPLA', 'HDFCBANK', 'BAJAJFINSV']
    
    chart_creator = UltraFocusedVCPCharts()
    
    created_charts = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] Creating ultra focused chart for {symbol}")
        print("-" * 45)
        
        chart_path = chart_creator.create_ultra_focused_chart(symbol)
        
        if chart_path:
            created_charts.append((symbol, chart_path))
            print(f"✅ SUCCESS: {chart_path}")
        else:
            print(f"❌ FAILED: No chart created")
    
    # Summary
    print(f"\n📊 ULTRA FOCUSED CHART CREATION COMPLETE!")
    print(f"Successfully created {len(created_charts)}/{len(symbols)} charts")
    
    if created_charts:
        print(f"\n✅ ULTRA FOCUSED CHARTS CREATED:")
        for symbol, path in created_charts:
            print(f"   🎯 {symbol:<12} → {path}")
        
        print(f"\n💡 ULTRA FOCUSED FEATURES:")
        print(f"   • Shows only recent 3-6 months of contractions")
        print(f"   • Individual contraction stats (duration, range%)")
        print(f"   • Clear volume analysis during contractions") 
        print(f"   • Focused timeline for actionable analysis")
        print(f"   • No long empty periods between events")

if __name__ == "__main__":
    main()