"""
Cup and Handle Chart Creator
============================

Creates professional charts for cup and handle patterns with educational
annotations and trading level analysis.
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
import seaborn as sns

# Set style
plt.style.use('seaborn-v0_8')

class CupHandleCharts:
    """Create detailed charts for cup and handle pattern analysis"""
    
    def __init__(self):
        self.data_service = DataService()
    
    def create_pattern_charts(self, symbols=None):
        """Create cup and handle charts for specified symbols"""
        
        if symbols is None:
            # Focus on symbols with potential patterns
            symbols = ['INFY', 'TCS', 'HCLTECH', 'WIPRO', 'RELIANCE', 'ASIANPAINT']
        
        print("🏆 CREATING CUP AND HANDLE CHARTS")
        print("=" * 60)
        
        created_charts = []
        
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] Creating chart for {symbol}")
            print("-" * 40)
            
            try:
                chart_path = self._create_pattern_chart(symbol)
                if chart_path:
                    created_charts.append((symbol, chart_path))
                    print(f"✅ SUCCESS: {chart_path}")
                else:
                    print(f"❌ FAILED: Could not create chart")
                    
            except Exception as e:
                print(f"❌ ERROR: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n🏆 CUP AND HANDLE CHARTS COMPLETE!")
        print(f"Successfully created {len(created_charts)}/{len(symbols)} charts")
        
        if created_charts:
            print(f"\n✅ CHARTS CREATED:")
            for symbol, path in created_charts:
                print(f"   📈 {symbol:<12} → {path}")
    
    def _create_pattern_chart(self, symbol):
        """Create cup and handle analysis chart for a single symbol"""
        
        # Get 18 months of data
        end_date = date.today()
        start_date = end_date - timedelta(days=550)
        
        data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
        data = self._filter_trading_days(data)
        
        if len(data) < 100:
            print(f"   ❌ Insufficient data: {len(data)} records")
            return None
        
        print(f"   📊 Data: {len(data)} trading days")
        
        # Analyze the pattern
        analysis = self._analyze_for_chart(data, symbol)
        
        if not analysis:
            print(f"   ❌ No suitable pattern found for charting")
            return None
        
        # Create the chart
        fig = self._create_detailed_chart(data, analysis, symbol)
        
        # Save chart
        save_path = f"charts/cup_handle_{symbol}.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path
    
    def _filter_trading_days(self, data):
        """Filter out weekends"""
        data['date'] = pd.to_datetime(data['date'])
        data = data[data['date'].dt.dayofweek < 5].copy()
        return data.reset_index(drop=True)
    
    def _analyze_for_chart(self, data, symbol):
        """Analyze data to find the best pattern for charting"""
        
        current_price = data.iloc[-1]['close']
        
        # Find major high and low points
        high_price = data['high'].max()
        high_idx = data['high'].idxmax()
        high_global_idx = data.index.get_loc(high_idx)
        high_date = data.iloc[high_global_idx]['date']
        
        low_price = data['low'].min()
        low_idx = data['low'].idxmin()
        low_global_idx = data.index.get_loc(low_idx)
        low_date = data.iloc[low_global_idx]['date']
        
        # Check if we have a basic cup shape (high → low → recovery)
        if low_global_idx <= high_global_idx:
            # Look for earlier high
            early_data = data.iloc[:low_global_idx]
            if len(early_data) > 0:
                high_price = early_data['high'].max()
                high_idx = early_data['high'].idxmax()
                high_global_idx = data.index.get_loc(high_idx)
                high_date = data.iloc[high_global_idx]['date']
        
        # Calculate cup metrics
        cup_depth = ((high_price - low_price) / high_price) * 100
        cup_duration = low_global_idx - high_global_idx if low_global_idx > high_global_idx else len(data) // 2
        
        # Find recent recovery level
        recent_data = data.tail(60)  # Last 60 days
        recent_high = recent_data['high'].max()
        recent_high_idx = recent_data['high'].idxmax()
        recent_high_global_idx = data.index.get_loc(recent_high_idx)
        
        # Calculate handle potential
        handle_data = data.iloc[recent_high_global_idx:]
        if len(handle_data) > 0:
            handle_low = handle_data['low'].min()
            handle_depth = ((recent_high - handle_low) / recent_high) * 100 if recent_high > handle_low else 0
        else:
            handle_low = current_price
            handle_depth = 0
        
        # Recovery percentage from cup bottom
        recovery_pct = ((recent_high - low_price) / (high_price - low_price)) * 100 if high_price > low_price else 0
        
        # Determine pattern status
        if recovery_pct >= 50 and cup_depth >= 10:
            if handle_depth >= 5:
                pattern_status = "Cup with Handle"
            elif recovery_pct >= 70:
                pattern_status = "Cup Formation (Developing Handle)"
            else:
                pattern_status = "Partial Cup Formation"
        else:
            pattern_status = "Early Cup Formation"
        
        # Calculate trading levels
        resistance_level = max(high_price, recent_high) * 0.98  # Slight discount
        breakout_level = resistance_level * 1.02
        stop_loss_level = max(handle_low, low_price * 1.05) * 0.97
        target_level = breakout_level + (high_price - low_price)  # Cup height projection
        
        return {
            'high_price': high_price,
            'high_idx': high_global_idx,
            'high_date': high_date,
            'low_price': low_price,
            'low_idx': low_global_idx,
            'low_date': low_date,
            'current_price': current_price,
            'cup_depth': cup_depth,
            'cup_duration': cup_duration,
            'recent_high': recent_high,
            'recent_high_idx': recent_high_global_idx,
            'handle_low': handle_low,
            'handle_depth': handle_depth,
            'recovery_percent': recovery_pct,
            'pattern_status': pattern_status,
            'resistance_level': resistance_level,
            'breakout_level': breakout_level,
            'stop_loss_level': stop_loss_level,
            'target_level': target_level,
            'distance_to_breakout': ((breakout_level - current_price) / current_price) * 100
        }
    
    def _create_detailed_chart(self, data, analysis, symbol):
        """Create the detailed cup and handle chart"""
        
        fig = plt.figure(figsize=(20, 14))
        
        # Create layout
        gs = fig.add_gridspec(4, 3, height_ratios=[3, 1, 1, 1], width_ratios=[2, 2, 1],
                             hspace=0.3, wspace=0.3)
        
        ax_price = fig.add_subplot(gs[0, :2])     # Main price chart
        ax_volume = fig.add_subplot(gs[1, :2])    # Volume chart
        ax_pattern = fig.add_subplot(gs[2, :2])   # Pattern analysis
        ax_info = fig.add_subplot(gs[:, 2])       # Info panel
        
        # Main title
        fig.suptitle(f'{symbol} - Cup and Handle Analysis: {analysis["pattern_status"]}', 
                    fontsize=18, fontweight='bold')
        
        # Plot components
        self._plot_price_analysis(ax_price, data, analysis, symbol)
        self._plot_volume_analysis(ax_volume, data, analysis)
        self._plot_pattern_measurements(ax_pattern, data, analysis)
        self._plot_info_panel(ax_info, analysis, symbol)
        
        return fig
    
    def _plot_price_analysis(self, ax, data, analysis, symbol):
        """Plot price chart with cup and handle annotations"""
        
        # Price line
        ax.plot(range(len(data)), data['close'], linewidth=2, color='#1f77b4', 
                label='Close Price', zorder=4)
        
        # Fill price range for volatility visualization
        ax.fill_between(range(len(data)), data['low'], data['high'], 
                       alpha=0.1, color='lightblue', zorder=1)
        
        # Mark key points
        # Cup high
        ax.plot(analysis['high_idx'], analysis['high_price'], 'o', markersize=12, 
               color='red', markeredgecolor='darkred', markeredgewidth=2, 
               label=f'Cup High: ₹{analysis["high_price"]:.0f}', zorder=5)
        
        # Cup bottom
        ax.plot(analysis['low_idx'], analysis['low_price'], 'o', markersize=12, 
               color='green', markeredgecolor='darkgreen', markeredgewidth=2, 
               label=f'Cup Bottom: ₹{analysis["low_price"]:.0f}', zorder=5)
        
        # Recent high (handle start)
        if analysis['recent_high_idx'] != analysis['high_idx']:
            ax.plot(analysis['recent_high_idx'], analysis['recent_high'], 'o', markersize=10, 
                   color='orange', markeredgecolor='darkorange', markeredgewidth=2, 
                   label=f'Handle Start: ₹{analysis["recent_high"]:.0f}', zorder=5)
        
        # Current price
        current_idx = len(data) - 1
        ax.plot(current_idx, analysis['current_price'], 'o', markersize=12, 
               color='yellow', markeredgecolor='black', markeredgewidth=2, 
               label=f'Current: ₹{analysis["current_price"]:.0f}', zorder=5)
        
        # Draw cup formation
        if analysis['high_idx'] < analysis['low_idx']:
            cup_indices = range(analysis['high_idx'], analysis['low_idx'] + 1)
            cup_prices = [data.iloc[i]['close'] for i in cup_indices]
            ax.plot(cup_indices, cup_prices, linewidth=4, color='blue', alpha=0.7, 
                   label='Cup Formation', zorder=3)
        
        # Draw handle if present
        if analysis['handle_depth'] > 5:
            handle_start = analysis['recent_high_idx']
            handle_indices = range(handle_start, len(data))
            handle_prices = [data.iloc[i]['close'] for i in handle_indices]
            ax.plot(handle_indices, handle_prices, linewidth=4, color='purple', alpha=0.7, 
                   label='Handle Formation', zorder=3)
        
        # Trading levels
        ax.axhline(y=analysis['resistance_level'], color='red', linestyle='--', 
                  linewidth=2, alpha=0.8, label=f'Resistance: ₹{analysis["resistance_level"]:.0f}')
        
        ax.axhline(y=analysis['breakout_level'], color='darkred', linestyle=':', 
                  linewidth=3, alpha=0.9, label=f'Breakout: ₹{analysis["breakout_level"]:.0f}')
        
        ax.axhline(y=analysis['stop_loss_level'], color='darkgreen', linestyle=':', 
                  linewidth=3, alpha=0.9, label=f'Stop Loss: ₹{analysis["stop_loss_level"]:.0f}')
        
        ax.axhline(y=analysis['target_level'], color='gold', linestyle=':', 
                  linewidth=3, alpha=0.9, label=f'Target: ₹{analysis["target_level"]:.0f}')
        
        # Cup depth annotation
        cup_mid_idx = (analysis['high_idx'] + analysis['low_idx']) // 2
        ax.annotate('', xy=(cup_mid_idx, analysis['high_price']), 
                   xytext=(cup_mid_idx, analysis['low_price']),
                   arrowprops=dict(arrowstyle='<->', color='red', lw=2))
        ax.text(cup_mid_idx + 5, (analysis['high_price'] + analysis['low_price']) / 2, 
               f'Cup Depth\n{analysis["cup_depth"]:.1f}%', 
               fontsize=10, fontweight='bold', ha='left', va='center',
               bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
        
        ax.set_ylabel('Price (₹)', fontsize=14, fontweight='bold')
        ax.legend(loc='upper left', fontsize=10, ncol=2)
        ax.grid(True, alpha=0.3)
        ax.set_title(f'Cup and Handle Pattern Analysis - {analysis["pattern_status"]}', 
                    fontsize=14, fontweight='bold')
        
        self._format_axis_dates(ax, data)
    
    def _plot_volume_analysis(self, ax, data, analysis):
        """Plot volume with cup and handle phase analysis"""
        
        # Volume bars
        colors = ['darkgreen' if close >= open_val else 'darkred' 
                 for close, open_val in zip(data['close'], data['open'])]
        
        ax.bar(range(len(data)), data['volume'], color=colors, alpha=0.6, width=0.8)
        
        # Volume moving average
        vol_ma20 = data['volume'].rolling(20, min_periods=1).mean()
        ax.plot(range(len(data)), vol_ma20, color='black', linewidth=2, 
               label='Volume MA(20)', alpha=0.8)
        
        # Highlight cup and handle phases with volume
        if analysis['high_idx'] < analysis['low_idx']:
            # Cup formation phase
            ax.axvspan(analysis['high_idx'], analysis['low_idx'], alpha=0.2, color='blue', 
                      label='Cup Phase', zorder=1)
        
        if analysis['handle_depth'] > 5:
            # Handle formation phase
            ax.axvspan(analysis['recent_high_idx'], len(data)-1, alpha=0.2, color='purple', 
                      label='Handle Phase', zorder=1)
        
        ax.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
        
        ax.set_ylabel('Volume', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_title('Volume Analysis - Should Decline in Cup, Increase on Breakout', 
                    fontsize=12, fontweight='bold')
        
        self._format_axis_dates(ax, data)
    
    def _plot_pattern_measurements(self, ax, data, analysis):
        """Plot pattern quality measurements"""
        
        # Create measurement bars
        measurements = {
            'Cup Depth': analysis['cup_depth'],
            'Recovery %': analysis['recovery_percent'],
            'Handle Depth': analysis['handle_depth'],
            'Distance to BO': abs(analysis['distance_to_breakout'])
        }
        
        # Color coding
        colors = []
        for key, value in measurements.items():
            if key == 'Cup Depth':
                if 20 <= value <= 35:
                    colors.append('green')
                elif 15 <= value <= 50:
                    colors.append('orange')
                else:
                    colors.append('red')
            elif key == 'Recovery %':
                if value >= 70:
                    colors.append('green')
                elif value >= 50:
                    colors.append('orange')
                else:
                    colors.append('red')
            elif key == 'Handle Depth':
                if value <= 25:
                    colors.append('green')
                elif value <= 40:
                    colors.append('orange')
                else:
                    colors.append('red')
            else:  # Distance to breakout
                if value <= 5:
                    colors.append('green')
                elif value <= 10:
                    colors.append('orange')
                else:
                    colors.append('red')
        
        bars = ax.bar(measurements.keys(), measurements.values(), color=colors, alpha=0.7)
        
        # Add value labels
        for bar, value in zip(bars, measurements.values()):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                   f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        ax.set_ylabel('Percentage', fontsize=12, fontweight='bold')
        ax.set_title('Pattern Quality Measurements', fontsize=12, fontweight='bold')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3)
    
    def _plot_info_panel(self, ax, analysis, symbol):
        """Plot comprehensive information panel"""
        
        ax.axis('off')
        
        # Pattern assessment
        if analysis['recovery_percent'] >= 70 and analysis['handle_depth'] >= 5:
            pattern_grade = "A - Excellent"
            grade_color = 'lightgreen'
        elif analysis['recovery_percent'] >= 50 and analysis['cup_depth'] <= 50:
            pattern_grade = "B - Good"
            grade_color = 'lightyellow'
        elif analysis['recovery_percent'] >= 30:
            pattern_grade = "C - Developing"
            grade_color = 'lightcyan'
        else:
            pattern_grade = "D - Early Stage"
            grade_color = 'lightcoral'
        
        info_text = f"""🏆 {symbol} - CUP & HANDLE ANALYSIS

📊 PATTERN STATUS:
   Type: {analysis['pattern_status']}
   Grade: {pattern_grade}

📏 CUP MEASUREMENTS:
   Cup High: ₹{analysis['high_price']:.2f}
   Cup Bottom: ₹{analysis['low_price']:.2f}
   Cup Depth: {analysis['cup_depth']:.1f}%
   Duration: {analysis['cup_duration']} days
   Recovery: {analysis['recovery_percent']:.1f}%

🔄 HANDLE MEASUREMENTS:
   Handle High: ₹{analysis['recent_high']:.2f}
   Handle Low: ₹{analysis['handle_low']:.2f}
   Handle Depth: {analysis['handle_depth']:.1f}%

🎯 TRADING LEVELS:
   Current Price: ₹{analysis['current_price']:.2f}
   Resistance: ₹{analysis['resistance_level']:.2f}
   Breakout Entry: ₹{analysis['breakout_level']:.2f}
   Stop Loss: ₹{analysis['stop_loss_level']:.2f}
   Target: ₹{analysis['target_level']:.2f}
   
📈 SETUP METRICS:
   Distance to Breakout: {analysis['distance_to_breakout']:.1f}%
   Risk/Reward: {(analysis['target_level'] - analysis['breakout_level']) / (analysis['breakout_level'] - analysis['stop_loss_level']):.1f}

📋 CUP & HANDLE CRITERIA:
   ✅ Optimal Cup Depth: 20-35%
   ✅ Recovery Required: >70%
   ✅ Handle Depth: <25%
   ✅ Volume: Decline in cup, surge on breakout

🎯 TRADING STRATEGY:
   • Wait for breakout above ₹{analysis['breakout_level']:.0f}
   • Enter on volume confirmation
   • Stop loss below ₹{analysis['stop_loss_level']:.0f}
   • Target ₹{analysis['target_level']:.0f}
   • Position size: 2-3% of portfolio

💡 WILLIAM O'NEIL RULES:
   • Cup: 7-65 weeks duration
   • Handle: 1-4 weeks, shallow pullback
   • Base depth: 15-35% optimal
   • Volume dry-up in cup essential
   • Breakout on strong volume"""
        
        ax.text(0.05, 0.95, info_text, transform=ax.transAxes, fontsize=9,
               verticalalignment='top', fontfamily='monospace',
               bbox=dict(boxstyle="round,pad=0.5", facecolor=grade_color, alpha=0.9))
    
    def _format_axis_dates(self, ax, data):
        """Format x-axis with dates"""
        
        ax.set_xlim(-0.5, len(data) - 0.5)
        
        # Select tick positions
        tick_interval = max(1, len(data) // 8)
        tick_positions = list(range(0, len(data), tick_interval))
        if tick_positions[-1] != len(data) - 1:
            tick_positions.append(len(data) - 1)
        
        tick_labels = [data.iloc[pos]['date'].strftime('%b %d') for pos in tick_positions]
        
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45)

def main():
    """Create cup and handle charts"""
    
    chart_creator = CupHandleCharts()
    chart_creator.create_pattern_charts()

if __name__ == "__main__":
    main()