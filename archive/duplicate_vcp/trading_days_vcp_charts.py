"""
Trading Days Only VCP Candlestick Charts
========================================
Create candlestick charts showing only trading days (no weekends) with proper OHLC visualization
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from mplfinance.original_flavor import candlestick_ohlc
import pandas as pd
import numpy as np
from datetime import date, timedelta
from volatility_patterns.data.data_service import DataService
from volatility_patterns.core.vcp_detector import VCPDetector
import seaborn as sns

# Set clean style
plt.style.use('seaborn-v0_8')

class TradingDaysVCPCharts:
    """Create candlestick charts showing only trading days with VCP patterns"""
    
    def __init__(self):
        self.data_service = DataService()
        self.detector = VCPDetector()
        
    def create_trading_days_chart(self, symbol):
        """Create a candlestick chart focusing only on trading days"""
        
        try:
            print(f"📊 Creating trading days candlestick chart for {symbol}...")
            
            # Get full year of data for pattern detection
            end_date = date.today()
            start_date = date(end_date.year - 1, 1, 1)
            
            print(f"   Scanning {symbol} for patterns...")
            data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
            
            if len(data) < 100:
                print(f"   ❌ Insufficient data: only {len(data)} records")
                return None
            
            # Filter out weekends (keep only trading days)
            data = self._filter_trading_days(data)
            print(f"   📅 Trading days after weekend filter: {len(data)}")
            
            # Detect patterns
            patterns = self.detector.detect_vcp_patterns(data, symbol)
            
            if not patterns:
                print(f"   ❌ No patterns found")
                return None
            
            # Get best pattern
            best_pattern = max(patterns, key=lambda p: p.quality_score)
            print(f"✅ Found pattern (Quality: {best_pattern.quality_score:.1f})")
            
            # Focus on recent contractions (last 6 months)
            cutoff_date = date.today() - timedelta(days=180)
            recent_contractions = [
                c for c in best_pattern.contractions 
                if c.end_date >= cutoff_date
            ]
            
            if not recent_contractions:
                # Take last 5 contractions if no recent ones
                recent_contractions = best_pattern.contractions[-5:] if len(best_pattern.contractions) > 5 else best_pattern.contractions
            
            if not recent_contractions:
                print(f"   ❌ No recent contractions found")
                return None
            
            # Calculate timeframe
            first_recent = min(c.start_date for c in recent_contractions)
            last_recent = max(c.end_date for c in recent_contractions)
            
            # Add buffer (3 weeks)
            buffer_days = 21
            focus_start = first_recent - timedelta(days=buffer_days)
            focus_end = last_recent + timedelta(days=buffer_days)
            
            # Get focused data and filter trading days
            focused_data = self.data_service.get_ohlcv_data(symbol, focus_start, focus_end)
            focused_data = self._filter_trading_days(focused_data)
            
            duration = (focus_end - focus_start).days
            trading_days = len(focused_data)
            
            print(f"   Recent contractions: {len(recent_contractions)} found")
            print(f"   Timeframe: {first_recent} to {last_recent}")
            print(f"   Chart focus: {focus_start} to {focus_end} ({trading_days} trading days)")
            
            # Create candlestick chart
            fig = self._create_candlestick_chart(focused_data, best_pattern, recent_contractions, 
                                               symbol, first_recent, last_recent)
            
            # Save chart
            save_path = f"charts/candlestick_{symbol}.png"
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Candlestick chart saved: {save_path}")
            return save_path
            
        except Exception as e:
            print(f"❌ Error creating candlestick chart for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _filter_trading_days(self, data):
        """Filter out weekends and keep only trading days"""
        # Convert to datetime if not already
        data['date'] = pd.to_datetime(data['date'])
        
        # Filter out weekends (Saturday=5, Sunday=6)
        data = data[data['date'].dt.dayofweek < 5].copy()
        
        # Reset index
        data = data.reset_index(drop=True)
        
        return data
    
    def _create_candlestick_chart(self, data, full_pattern, recent_contractions, 
                                symbol, cont_start, cont_end):
        """Create the candlestick chart"""
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 12), 
                                      gridspec_kw={'height_ratios': [3, 1]})
        
        trading_days = len(data)
        duration = (cont_end - cont_start).days
        
        # Main title
        fig.suptitle(f'{symbol} - VCP Candlestick Analysis (Quality: {full_pattern.quality_score:.1f}, {trading_days} trading days)', 
                    fontsize=16, fontweight='bold')
        
        # Plot candlestick chart
        self._plot_candlestick_price(ax1, data, full_pattern, recent_contractions, 
                                   symbol, cont_start, cont_end)
        
        # Plot volume
        self._plot_candlestick_volume(ax2, data, recent_contractions)
        
        # Format x-axis for both subplots
        self._format_trading_days_axis(ax1, data, trading_days)
        self._format_trading_days_axis(ax2, data, trading_days)
        
        plt.tight_layout()
        return fig
    
    def _plot_candlestick_price(self, ax, data, full_pattern, recent_contractions, 
                              symbol, cont_start, cont_end):
        """Plot candlestick price chart"""
        
        # Prepare data for candlestick plot - use sequential positions instead of dates
        ohlc_data = data[['date', 'open', 'high', 'low', 'close']].copy()
        
        # Create sequential x-positions (no weekend gaps)
        ohlc_data['x_pos'] = range(len(ohlc_data))
        ohlc_values = ohlc_data[['x_pos', 'open', 'high', 'low', 'close']].values
        
        # Plot candlesticks
        candlestick_ohlc(ax, ohlc_values, width=0.6, colorup='green', colordown='red', alpha=0.8)
        
        # Mark recent contractions with background colors
        contraction_colors = ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
        
        for i, contraction in enumerate(recent_contractions):
            color = contraction_colors[i % len(contraction_colors)]
            
            # Find start and end positions for contractions
            start_mask = data['date'] >= pd.to_datetime(contraction.start_date)
            end_mask = data['date'] <= pd.to_datetime(contraction.end_date)
            
            if start_mask.any() and end_mask.any():
                start_pos = data[start_mask].index[0]
                end_pos = data[end_mask].index[-1]
                
                # Highlight contraction period
                ax.axvspan(start_pos, end_pos, alpha=0.2, color=color, zorder=1)
            
            # Calculate contraction stats
            cont_mask = ((data['date'] >= pd.to_datetime(contraction.start_date)) & 
                        (data['date'] <= pd.to_datetime(contraction.end_date)))
            cont_data = data[cont_mask]
            
            if len(cont_data) > 0:
                price_range = ((cont_data['high'].max() - cont_data['low'].min()) / 
                             cont_data['low'].min()) * 100
                duration = (contraction.end_date - contraction.start_date).days
                
                # Add contraction label
                mid_pos = (start_pos + end_pos) / 2
                label_text = f'C{i+1}\n{duration}d\n{price_range:.1f}%'
                
                ax.text(mid_pos, data['high'].max() * 0.98, label_text, 
                       ha='center', va='top', fontweight='bold', fontsize=9,
                       bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.7))
        
        # Support and resistance levels
        recent_data = data[(data['date'] >= pd.to_datetime(cont_start)) & 
                          (data['date'] <= pd.to_datetime(cont_end))]
        
        if len(recent_data) > 0:
            resistance = recent_data['high'].max()
            support = recent_data['low'].min()
            
            ax.axhline(y=resistance, color='red', linestyle='--', linewidth=2, 
                      alpha=0.7, label=f'Resistance: ₹{resistance:.0f}')
            ax.axhline(y=support, color='green', linestyle='--', linewidth=2, 
                      alpha=0.7, label=f'Support: ₹{support:.0f}')
        
        # Moving averages
        if len(data) > 20:
            ma20 = data['close'].rolling(20, min_periods=1).mean()
            ax.plot(range(len(data)), ma20, '--', alpha=0.7, 
                   color='orange', linewidth=2, label='MA20')
        
        if len(data) > 50:
            ma50 = data['close'].rolling(50, min_periods=1).mean()
            ax.plot(range(len(data)), ma50, '--', alpha=0.7, 
                   color='purple', linewidth=2, label='MA50')
        
        # Current price
        current_price = data['close'].iloc[-1]
        ax.axhline(y=current_price, color='blue', linestyle='-.', linewidth=2,
                  alpha=0.8, label=f'Current: ₹{current_price:.0f}')
        
        # Pattern info box
        info_text = f"""Pattern Analysis:
Quality: {full_pattern.quality_score:.1f}/100
Recent Contractions: {len(recent_contractions)}
Total Contractions: {len(full_pattern.contractions)}
Trading Days: {len(data)}"""
        
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle="round,pad=0.4", 
                facecolor='lightyellow', alpha=0.9))
        
        ax.set_ylabel('Price (₹)', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_title('VCP Candlestick Chart - Trading Days Only', fontsize=14, fontweight='bold')
    
    def _plot_candlestick_volume(self, ax, data, recent_contractions):
        """Plot volume bars for trading days"""
        
        # Volume bars with color coding - use sequential positions
        colors = ['darkgreen' if close >= open_val else 'darkred' 
                 for close, open_val in zip(data['close'], data['open'])]
        
        x_positions = range(len(data))
        bars = ax.bar(x_positions, data['volume'], color=colors, alpha=0.6, width=0.6)
        
        # Volume moving average
        if len(data) > 10:
            vol_ma = data['volume'].rolling(10, min_periods=1).mean()
            ax.plot(x_positions, vol_ma, color='black', linewidth=2.5, 
                   label='Vol MA(10)', alpha=0.8)
        
        # Average volume line
        avg_volume = data['volume'].mean()
        ax.axhline(y=avg_volume, color='blue', linestyle=':', linewidth=2,
                  alpha=0.7, label=f'Avg Volume: {avg_volume:,.0f}')
        
        # Highlight contraction periods on volume
        contraction_colors = ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
        
        for i, contraction in enumerate(recent_contractions):
            color = contraction_colors[i % len(contraction_colors)]
            
            # Find start and end positions for contractions
            start_mask = data['date'] >= pd.to_datetime(contraction.start_date)
            end_mask = data['date'] <= pd.to_datetime(contraction.end_date)
            
            if start_mask.any() and end_mask.any():
                start_pos = data[start_mask].index[0]
                end_pos = data[end_mask].index[-1]
                ax.axvspan(start_pos, end_pos, alpha=0.15, color=color, zorder=1)
        
        # Format volume numbers
        ax.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
        
        ax.set_ylabel('Volume', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_title('Volume Analysis - Trading Days Only', fontsize=12, fontweight='bold')
    
    def _format_trading_days_axis(self, ax, data, trading_days):
        """Format x-axis to show trading days without weekend gaps"""
        
        # Set x-axis limits to data range
        ax.set_xlim(-0.5, len(data) - 0.5)
        
        # Create custom tick positions and labels
        if trading_days <= 30:  # 1 month - show every 5th day
            tick_interval = 5
        elif trading_days <= 60:  # 2 months - show every 10th day
            tick_interval = 10
        else:  # More than 2 months - show every 15th day
            tick_interval = 15
        
        # Get tick positions
        tick_positions = list(range(0, len(data), tick_interval))
        if tick_positions[-1] != len(data) - 1:
            tick_positions.append(len(data) - 1)
        
        # Get corresponding dates
        tick_labels = [data.iloc[pos]['date'].strftime('%b %d') for pos in tick_positions]
        
        # Set ticks and labels
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45)
        
        # Add grid for better readability
        ax.grid(True, alpha=0.3, axis='x')

def main():
    """Create trading days candlestick charts"""
    
    print("📊 CREATING TRADING DAYS CANDLESTICK CHARTS")
    print("=" * 60)
    print("Features: Candlesticks + No Weekends + VCP Analysis")
    
    # Test with a few symbols
    symbols = ['CIPLA', 'HDFCBANK', 'BAJAJFINSV']
    
    chart_creator = TradingDaysVCPCharts()
    
    created_charts = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] Creating candlestick chart for {symbol}")
        print("-" * 50)
        
        chart_path = chart_creator.create_trading_days_chart(symbol)
        
        if chart_path:
            created_charts.append((symbol, chart_path))
            print(f"✅ SUCCESS: {chart_path}")
        else:
            print(f"❌ FAILED: No chart created")
    
    # Summary
    print(f"\n📊 CANDLESTICK CHART CREATION COMPLETE!")
    print(f"Successfully created {len(created_charts)}/{len(symbols)} charts")
    
    if created_charts:
        print(f"\n✅ CANDLESTICK CHARTS CREATED:")
        for symbol, path in created_charts:
            print(f"   📊 {symbol:<12} → {path}")
        
        print(f"\n💡 CANDLESTICK CHART FEATURES:")
        print(f"   • 📊 Full OHLC candlestick visualization")
        print(f"   • 📅 Trading days only (weekends excluded)")
        print(f"   • 🎯 VCP contractions clearly marked")
        print(f"   • 📈 Moving averages (20, 50 day)")
        print(f"   • 📊 Volume analysis with MA")
        print(f"   • 🎨 Color-coded contractions with stats")

if __name__ == "__main__":
    main()