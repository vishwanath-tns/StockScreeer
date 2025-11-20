"""
Volatility Setup Charts - Detailed Analysis of Top Opportunities
===============================================================

Creates professional charts for stocks showing volatility contraction
with clear trading levels and setup analysis.
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

class VolatilitySetupCharts:
    """Create detailed charts for volatility-based trading setups"""
    
    def __init__(self):
        self.data_service = DataService()
        
    def create_setup_charts(self, symbols=None):
        """Create charts for top volatility setups"""
        
        if symbols is None:
            # Top setups from our screener
            symbols = [
                'SBIN',       # Score 90 - Strong Buy
                'HCLTECH',    # Score 85 - Strong Buy  
                'SBILIFE',    # Score 85 - Strong Buy
                'RELIANCE',   # Score 80 - Strong Buy
                'SUNPHARMA',  # Score 78 - Strong Buy
                'M&M',        # Score 95 - Buy Setup
                'VEDL',       # Score 95 - Buy Setup
                'IOC'         # Score 95 - Buy Setup
            ]
        
        print("📊 CREATING VOLATILITY SETUP CHARTS")
        print("=" * 60)
        print("Top opportunities with trading levels and analysis...")
        
        created_charts = []
        
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] Creating chart for {symbol}")
            print("-" * 40)
            
            try:
                chart_path = self.create_single_setup_chart(symbol)
                if chart_path:
                    created_charts.append((symbol, chart_path))
                    print(f"✅ SUCCESS: {chart_path}")
                else:
                    print(f"❌ FAILED: Could not create chart")
                    
            except Exception as e:
                print(f"❌ ERROR: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n📊 VOLATILITY SETUP CHARTS COMPLETE!")
        print(f"Successfully created {len(created_charts)}/{len(symbols)} charts")
        
        if created_charts:
            print(f"\n✅ CHARTS CREATED:")
            for symbol, path in created_charts:
                print(f"   📈 {symbol:<12} → {path}")
            
            print(f"\n💡 CHART FEATURES:")
            print(f"   📏 Volatility contraction analysis")
            print(f"   🎯 Precise breakout and breakdown levels")
            print(f"   📊 Volume analysis and trend confirmation")
            print(f"   🔢 Setup scoring and recommendation")
            print(f"   📈 Moving averages and technical indicators")
    
    def create_single_setup_chart(self, symbol):
        """Create detailed setup chart for a single stock"""
        
        try:
            # Get data (4 months)
            end_date = date.today()
            start_date = end_date - timedelta(days=120)
            
            data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
            data = self._filter_trading_days(data)
            
            if len(data) < 60:
                print(f"   ❌ Insufficient data: {len(data)} records")
                return None
            
            print(f"   📊 Data: {len(data)} trading days")
            
            # Calculate all metrics
            analysis = self._analyze_setup(data, symbol)
            
            # Create chart
            fig = self._create_detailed_chart(data, analysis, symbol)
            
            # Save chart
            save_path = f"charts/volatility_setup_{symbol}.png"
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return save_path
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None
    
    def _filter_trading_days(self, data):
        """Filter out weekends"""
        data['date'] = pd.to_datetime(data['date'])
        data = data[data['date'].dt.dayofweek < 5].copy()
        return data.reset_index(drop=True)
    
    def _analyze_setup(self, data, symbol):
        """Analyze the volatility setup"""
        
        current_price = data.iloc[-1]['close']
        
        # Volatility analysis
        recent_30 = data.tail(30)
        recent_60 = data.tail(60)
        
        vol_30d = ((recent_30['high'].max() - recent_30['low'].min()) / recent_30['low'].min()) * 100
        vol_60d = ((recent_60['high'].max() - recent_60['low'].min()) / recent_60['low'].min()) * 100
        
        vol_ratio = vol_30d / vol_60d if vol_60d > 0 else 1
        
        if vol_ratio < 0.7:
            vol_trend = "Contracting"
        elif vol_ratio > 1.3:
            vol_trend = "Expanding"
        else:
            vol_trend = "Stable"
        
        # Trading levels
        resistance = recent_60['high'].max()
        support = recent_60['low'].max()  # Highest low
        
        # Alternative support (more conservative)
        lows_sorted = recent_60['low'].sort_values(ascending=False)
        if len(lows_sorted) >= 3:
            support = lows_sorted.iloc[2]
        
        breakout_level = resistance * 1.02
        breakdown_level = support * 0.98
        
        # Moving averages
        data['sma20'] = data['close'].rolling(20, min_periods=1).mean()
        data['sma50'] = data['close'].rolling(50, min_periods=1).mean()
        
        current_sma20 = data.iloc[-1]['sma20']
        current_sma50 = data.iloc[-1]['sma50']
        
        # Volume analysis
        avg_volume = data['volume'].tail(20).mean()
        recent_volume = data['volume'].tail(5).mean()
        
        # Calculate setup score
        score = self._calculate_detailed_score(
            vol_trend, current_price, breakout_level, 
            current_sma20, current_sma50, recent_volume, avg_volume
        )
        
        # Recommendation
        distance_pct = ((breakout_level - current_price) / current_price) * 100
        
        if score >= 75 and distance_pct <= 3:
            recommendation = "🔥 Strong Buy Setup"
        elif score >= 60 and distance_pct <= 5:
            recommendation = "⚡ Buy Setup"
        elif score >= 45:
            recommendation = "👀 Watch"
        else:
            recommendation = "💤 Avoid"
        
        return {
            'current_price': current_price,
            'vol_30d': vol_30d,
            'vol_60d': vol_60d,
            'vol_trend': vol_trend,
            'vol_ratio': vol_ratio,
            'resistance': resistance,
            'support': support,
            'breakout_level': breakout_level,
            'breakdown_level': breakdown_level,
            'distance_to_breakout': distance_pct,
            'distance_to_support': ((current_price - support) / support) * 100,
            'above_sma20': current_price > current_sma20,
            'above_sma50': current_price > current_sma50,
            'avg_volume': avg_volume,
            'recent_volume': recent_volume,
            'setup_score': score,
            'recommendation': recommendation
        }
    
    def _calculate_detailed_score(self, vol_trend, current_price, breakout_level,
                                sma20, sma50, recent_vol, avg_vol):
        """Calculate detailed setup score"""
        
        score = 0
        
        # Volatility (25 points)
        if vol_trend == "Contracting":
            score += 25
        elif vol_trend == "Stable":
            score += 15
        else:
            score += 5
        
        # Distance to breakout (20 points)
        distance_pct = ((breakout_level - current_price) / current_price) * 100
        if distance_pct <= 2:
            score += 20
        elif distance_pct <= 5:
            score += 15
        elif distance_pct <= 10:
            score += 10
        
        # Technical position (25 points)
        if current_price > sma20 and current_price > sma50:
            score += 25
        elif current_price > sma20:
            score += 15
        elif current_price > sma50:
            score += 10
        
        # SMA relationship (15 points)
        if sma20 > sma50:
            score += 15
        
        # Volume (15 points)
        vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1
        if 0.8 <= vol_ratio <= 1.2:
            score += 15  # Normal volume
        elif vol_ratio < 0.8:
            score += 10  # Low volume
        else:
            score += 5   # High volume
        
        return min(score, 100)
    
    def _create_detailed_chart(self, data, analysis, symbol):
        """Create the detailed setup chart"""
        
        fig = plt.figure(figsize=(20, 14))
        
        # Create layout
        gs = fig.add_gridspec(4, 3, height_ratios=[3, 1, 1, 1], width_ratios=[2, 2, 1],
                             hspace=0.3, wspace=0.3)
        
        ax_price = fig.add_subplot(gs[0, :2])     # Price chart
        ax_volume = fig.add_subplot(gs[1, :2])    # Volume chart
        ax_volatility = fig.add_subplot(gs[2, :2]) # Volatility chart
        ax_info = fig.add_subplot(gs[:, 2])       # Info panel
        
        # Main title
        score_color = "green" if analysis['setup_score'] >= 70 else "orange" if analysis['setup_score'] >= 50 else "red"
        fig.suptitle(f'{symbol} - Volatility Setup Analysis (Score: {analysis["setup_score"]:.0f})', 
                    fontsize=18, fontweight='bold', color=score_color)
        
        # Plot components
        self._plot_price_analysis(ax_price, data, analysis, symbol)
        self._plot_volume_analysis(ax_volume, data, analysis)
        self._plot_volatility_analysis(ax_volatility, data, analysis)
        self._plot_info_panel(ax_info, analysis, symbol)
        
        return fig
    
    def _plot_price_analysis(self, ax, data, analysis, symbol):
        """Plot price with trading levels"""
        
        # Price line
        ax.plot(range(len(data)), data['close'], linewidth=2.5, color='#1f77b4', 
                label='Close Price', zorder=4)
        
        # High-low range (volatility visualization)
        ax.fill_between(range(len(data)), data['low'], data['high'], 
                       alpha=0.15, color='lightblue', label='Daily Range', zorder=1)
        
        # Moving averages
        ax.plot(range(len(data)), data['sma20'], '--', alpha=0.8, color='orange', 
               linewidth=2, label='SMA 20', zorder=3)
        ax.plot(range(len(data)), data['sma50'], '--', alpha=0.8, color='red', 
               linewidth=2, label='SMA 50', zorder=3)
        
        # Trading levels
        ax.axhline(y=analysis['resistance'], color='red', linestyle='-', linewidth=3, 
                  alpha=0.8, label=f'Resistance: ₹{analysis["resistance"]:.0f}')
        ax.axhline(y=analysis['support'], color='green', linestyle='-', linewidth=3, 
                  alpha=0.8, label=f'Support: ₹{analysis["support"]:.0f}')
        
        # Breakout/breakdown levels
        ax.axhline(y=analysis['breakout_level'], color='darkred', linestyle=':', 
                  linewidth=4, alpha=0.9, label=f'Breakout: ₹{analysis["breakout_level"]:.0f}')
        ax.axhline(y=analysis['breakdown_level'], color='darkgreen', linestyle=':', 
                  linewidth=4, alpha=0.9, label=f'Breakdown: ₹{analysis["breakdown_level"]:.0f}')
        
        # Current price marker
        current_idx = len(data) - 1
        current_price = analysis['current_price']
        ax.plot(current_idx, current_price, 'o', markersize=12, color='yellow', 
               markeredgecolor='black', markeredgewidth=2, zorder=5)
        ax.text(current_idx + 1, current_price, f'₹{current_price:.0f}', 
               fontsize=12, fontweight='bold', va='center')
        
        # Volatility contraction zones
        if analysis['vol_trend'] == "Contracting":
            # Highlight recent consolidation
            recent_start = max(0, len(data) - 30)
            ax.axvspan(recent_start, len(data)-1, alpha=0.2, color='green', 
                      label='Contraction Zone', zorder=2)
        
        ax.set_ylabel('Price (₹)', fontsize=14, fontweight='bold')
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        title_color = "green" if analysis['vol_trend'] == "Contracting" else "orange"
        ax.set_title(f'Price Action & Trading Levels - {analysis["vol_trend"]} Volatility', 
                    fontsize=14, fontweight='bold', color=title_color)
        
        # Format x-axis
        self._format_axis_dates(ax, data)
    
    def _plot_volume_analysis(self, ax, data, analysis):
        """Plot volume analysis"""
        
        # Volume bars
        colors = ['darkgreen' if close >= open_val else 'darkred' 
                 for close, open_val in zip(data['close'], data['open'])]
        
        ax.bar(range(len(data)), data['volume'], color=colors, alpha=0.6, width=0.8)
        
        # Volume averages
        vol_ma10 = data['volume'].rolling(10, min_periods=1).mean()
        vol_ma20 = data['volume'].rolling(20, min_periods=1).mean()
        
        ax.plot(range(len(data)), vol_ma10, color='purple', linewidth=2, 
               label='Vol MA(10)', alpha=0.8)
        ax.plot(range(len(data)), vol_ma20, color='black', linewidth=2, 
               label='Vol MA(20)', alpha=0.8)
        
        # Average volume line
        ax.axhline(y=analysis['avg_volume'], color='blue', linestyle='--', 
                  linewidth=2, alpha=0.7, label=f'Avg Vol: {analysis["avg_volume"]/1e6:.1f}M')
        
        ax.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
        
        ax.set_ylabel('Volume', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_title('Volume Analysis - Ideal: Steady/Declining in Consolidation', 
                    fontsize=12, fontweight='bold')
        
        self._format_axis_dates(ax, data)
    
    def _plot_volatility_analysis(self, ax, data, analysis):
        """Plot volatility analysis"""
        
        # Calculate rolling volatility
        window = 20
        volatility = []
        
        for i in range(window, len(data)):
            period_data = data.iloc[i-window:i+1]
            vol = ((period_data['high'].max() - period_data['low'].min()) / 
                   period_data['low'].min()) * 100
            volatility.append(vol)
        
        vol_indices = list(range(window, len(data)))
        
        # Plot volatility
        ax.plot(vol_indices, volatility, color='purple', linewidth=3, 
               label='20-day Volatility %', alpha=0.8)
        
        # Add trend line
        if len(volatility) > 10:
            z = np.polyfit(vol_indices, volatility, 1)
            p = np.poly1d(z)
            ax.plot(vol_indices, p(vol_indices), "r--", alpha=0.8, linewidth=2,
                   label='Volatility Trend')
        
        # Highlight volatility zones
        if analysis['vol_trend'] == "Contracting":
            ax.axhspan(0, max(volatility) * 0.5, alpha=0.2, color='green', 
                      label='Low Volatility Zone')
        
        # Current volatility markers
        ax.axhline(y=analysis['vol_30d'], color='red', linestyle=':', 
                  linewidth=2, label=f'30d Vol: {analysis["vol_30d"]:.1f}%')
        ax.axhline(y=analysis['vol_60d'], color='blue', linestyle=':', 
                  linewidth=2, label=f'60d Vol: {analysis["vol_60d"]:.1f}%')
        
        ax.set_ylabel('Volatility %', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)
        
        title_text = f'Volatility Trend: {analysis["vol_trend"]} (Ratio: {analysis["vol_ratio"]:.2f})'
        ax.set_title(title_text, fontsize=12, fontweight='bold')
        
        self._format_axis_dates(ax, data)
    
    def _plot_info_panel(self, ax, analysis, symbol):
        """Plot information panel"""
        
        ax.axis('off')
        
        # Setup info
        info_text = f"""📊 {symbol} - VOLATILITY SETUP ANALYSIS

🎯 TRADING LEVELS:
   Current Price: ₹{analysis['current_price']:.2f}
   Resistance: ₹{analysis['resistance']:.2f}
   Support: ₹{analysis['support']:.2f}
   
🚀 ENTRY/EXIT LEVELS:
   Breakout Entry: ₹{analysis['breakout_level']:.2f}
   ({analysis['distance_to_breakout']:+.1f}% from current)
   
   Breakdown Exit: ₹{analysis['breakdown_level']:.2f}
   ({analysis['distance_to_support']:+.1f}% cushion)

📈 VOLATILITY ANALYSIS:
   30-day Range: {analysis['vol_30d']:.1f}%
   60-day Range: {analysis['vol_60d']:.1f}%
   Trend: {analysis['vol_trend']}
   Ratio: {analysis['vol_ratio']:.2f}

📊 TECHNICAL POSITION:
   Above SMA20: {'✅' if analysis['above_sma20'] else '❌'}
   Above SMA50: {'✅' if analysis['above_sma50'] else '❌'}
   
📦 VOLUME ANALYSIS:
   Recent vs Avg: {analysis['recent_volume']/analysis['avg_volume']:.2f}x
   Status: {'Normal' if 0.8 <= analysis['recent_volume']/analysis['avg_volume'] <= 1.2 else 'High' if analysis['recent_volume']/analysis['avg_volume'] > 1.2 else 'Low'}

🔢 SETUP SCORE: {analysis['setup_score']:.0f}/100

🎯 RECOMMENDATION:
   {analysis['recommendation']}

💡 TRADING STRATEGY:
   • Wait for breakout above ₹{analysis['breakout_level']:.0f}
   • Enter with 2-3% position size
   • Stop loss below ₹{analysis['breakdown_level']:.0f}
   • Target: 15-25% gain potential
   • Risk:Reward ≈ 1:3"""
        
        # Color code based on recommendation
        if "Strong Buy" in analysis['recommendation']:
            bg_color = 'lightgreen'
        elif "Buy" in analysis['recommendation']:
            bg_color = 'lightyellow'
        elif "Watch" in analysis['recommendation']:
            bg_color = 'lightcyan'
        else:
            bg_color = 'lightcoral'
        
        ax.text(0.05, 0.95, info_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', fontfamily='monospace',
               bbox=dict(boxstyle="round,pad=0.5", facecolor=bg_color, alpha=0.9))
    
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
    """Create volatility setup charts"""
    
    chart_creator = VolatilitySetupCharts()
    chart_creator.create_setup_charts()

if __name__ == "__main__":
    main()