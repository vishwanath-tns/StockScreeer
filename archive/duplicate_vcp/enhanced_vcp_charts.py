"""
Enhanced VCP Candlestick Charts with Professional Trading Features
=================================================================
Add VCP-specific analysis: Volume dry-up, breakout zones, stage analysis, relative strength
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

class EnhancedVCPCharts:
    """Create enhanced VCP candlestick charts with professional trading features"""
    
    def __init__(self):
        self.data_service = DataService()
        self.detector = VCPDetector()
        
    def create_enhanced_vcp_chart(self, symbol):
        """Create enhanced VCP chart with all professional features"""
        
        try:
            print(f"📊 Creating enhanced VCP chart for {symbol}...")
            
            # Get full year of data for pattern detection
            end_date = date.today()
            start_date = date(end_date.year - 1, 1, 1)
            
            print(f"   Scanning {symbol} for patterns...")
            data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
            
            if len(data) < 100:
                print(f"   ❌ Insufficient data: only {len(data)} records")
                return None
            
            # Filter trading days
            data = self._filter_trading_days(data)
            print(f"   📅 Trading days: {len(data)}")
            
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
                recent_contractions = best_pattern.contractions[-5:] if len(best_pattern.contractions) > 5 else best_pattern.contractions
            
            if not recent_contractions:
                print(f"   ❌ No recent contractions found")
                return None
            
            # Calculate timeframe
            first_recent = min(c.start_date for c in recent_contractions)
            last_recent = max(c.end_date for c in recent_contractions)
            
            # Add buffer
            buffer_days = 21
            focus_start = first_recent - timedelta(days=buffer_days)
            focus_end = last_recent + timedelta(days=buffer_days)
            
            # Get focused data
            focused_data = self.data_service.get_ohlcv_data(symbol, focus_start, focus_end)
            focused_data = self._filter_trading_days(focused_data)
            
            trading_days = len(focused_data)
            print(f"   Chart focus: {focus_start} to {focus_end} ({trading_days} trading days)")
            
            # Create enhanced chart
            fig = self._create_enhanced_chart(focused_data, best_pattern, recent_contractions, 
                                            symbol, first_recent, last_recent)
            
            # Save chart
            save_path = f"charts/enhanced_{symbol}.png"
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Enhanced chart saved: {save_path}")
            return save_path
            
        except Exception as e:
            print(f"❌ Error creating enhanced chart for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _filter_trading_days(self, data):
        """Filter out weekends"""
        data['date'] = pd.to_datetime(data['date'])
        data = data[data['date'].dt.dayofweek < 5].copy()
        return data.reset_index(drop=True)
    
    def _create_enhanced_chart(self, data, full_pattern, recent_contractions, 
                             symbol, cont_start, cont_end):
        """Create the enhanced chart with all VCP features"""
        
        fig = plt.figure(figsize=(22, 14))
        
        # Create grid layout: Price (top), Volume (middle), VCP Analysis (bottom)
        gs = fig.add_gridspec(3, 2, height_ratios=[3, 1, 1], width_ratios=[3, 1], 
                             hspace=0.3, wspace=0.2)
        
        ax_price = fig.add_subplot(gs[0, :])  # Price spans both columns
        ax_volume = fig.add_subplot(gs[1, :])  # Volume spans both columns  
        ax_analysis = fig.add_subplot(gs[2, 0])  # VCP analysis left
        ax_stats = fig.add_subplot(gs[2, 1])  # Stats right
        
        trading_days = len(data)
        
        # Main title
        fig.suptitle(f'{symbol} - Enhanced VCP Analysis (Quality: {full_pattern.quality_score:.1f}, {trading_days} trading days)', 
                    fontsize=18, fontweight='bold')
        
        # Plot enhanced components
        self._plot_enhanced_price(ax_price, data, full_pattern, recent_contractions, symbol, cont_start, cont_end)
        self._plot_enhanced_volume(ax_volume, data, recent_contractions)
        self._plot_vcp_analysis(ax_analysis, recent_contractions)
        self._plot_pattern_stats(ax_stats, full_pattern, recent_contractions, data)
        
        # Format axes
        self._format_trading_axis(ax_price, data)
        self._format_trading_axis(ax_volume, data)
        
        return fig
    
    def _plot_enhanced_price(self, ax, data, full_pattern, recent_contractions, symbol, cont_start, cont_end):
        """Enhanced price chart with VCP-specific features"""
        
        # Candlesticks
        ohlc_data = data[['date', 'open', 'high', 'low', 'close']].copy()
        ohlc_data['x_pos'] = range(len(ohlc_data))
        ohlc_values = ohlc_data[['x_pos', 'open', 'high', 'low', 'close']].values
        candlestick_ohlc(ax, ohlc_values, width=0.6, colorup='green', colordown='red', alpha=0.8)
        
        # Mark contractions with volume analysis
        contraction_colors = ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
        
        for i, contraction in enumerate(recent_contractions):
            color = contraction_colors[i % len(contraction_colors)]
            
            # Find positions
            start_mask = data['date'] >= pd.to_datetime(contraction.start_date)
            end_mask = data['date'] <= pd.to_datetime(contraction.end_date)
            
            if start_mask.any() and end_mask.any():
                start_pos = data[start_mask].index[0]
                end_pos = data[end_mask].index[-1]
                
                # Highlight contraction
                ax.axvspan(start_pos, end_pos, alpha=0.15, color=color, zorder=1)
                
                # Calculate contraction stats
                cont_data = data[(data['date'] >= pd.to_datetime(contraction.start_date)) & 
                               (data['date'] <= pd.to_datetime(contraction.end_date))]
                
                if len(cont_data) > 0:
                    price_range = ((cont_data['high'].max() - cont_data['low'].min()) / 
                                 cont_data['low'].min()) * 100
                    duration = (contraction.end_date - contraction.start_date).days
                    avg_volume = cont_data['volume'].mean()
                    
                    # Volume dry-up indicator
                    prev_avg_volume = data.iloc[:start_pos]['volume'].tail(10).mean() if start_pos > 10 else avg_volume
                    volume_decline = ((prev_avg_volume - avg_volume) / prev_avg_volume) * 100 if prev_avg_volume > 0 else 0
                    
                    # Enhanced label with volume info
                    mid_pos = (start_pos + end_pos) / 2
                    volume_indicator = "📉" if volume_decline > 20 else "📊" if volume_decline > 0 else "📈"
                    label_text = f'C{i+1} {volume_indicator}\n{duration}d | {price_range:.1f}%\nVol: {volume_decline:.0f}%'
                    
                    ax.text(mid_pos, data['high'].max() * 0.98, label_text, 
                           ha='center', va='top', fontweight='bold', fontsize=8,
                           bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.8))
        
        # Support and Resistance
        recent_data = data[(data['date'] >= pd.to_datetime(cont_start)) & 
                          (data['date'] <= pd.to_datetime(cont_end))]
        
        if len(recent_data) > 0:
            resistance = recent_data['high'].max()
            support = recent_data['low'].min()
            current_price = data['close'].iloc[-1]
            
            # Key trading levels
            entry_level = resistance * 1.02  # 2% above resistance for entry
            breakout_level = resistance * 1.05  # 5% above resistance
            stop_loss = support * 0.98  # 2% below support
            target_level = entry_level * 1.25  # 25% above entry
            
            # Plot the levels with clear labels
            ax.axhline(y=resistance, color='red', linestyle='--', linewidth=2, 
                      alpha=0.8, label=f'Resistance: ₹{resistance:.0f}')
            ax.axhline(y=support, color='green', linestyle='--', linewidth=2, 
                      alpha=0.8, label=f'Support: ₹{support:.0f}')
            
            # ENTRY LEVEL - Blue dotted line
            ax.axhline(y=entry_level, color='blue', linestyle=':', linewidth=3,
                      alpha=0.9, label=f'🎯 ENTRY: ₹{entry_level:.0f}')
            
            # STOP LOSS - Red solid line  
            ax.axhline(y=stop_loss, color='darkred', linestyle='-', linewidth=3,
                      alpha=0.9, label=f'🛑 STOP: ₹{stop_loss:.0f}')
            
            # TARGET - Green solid line
            ax.axhline(y=target_level, color='darkgreen', linestyle='-', linewidth=3,
                      alpha=0.9, label=f'🎯 TARGET: ₹{target_level:.0f}')
            
            # Breakout zone (visual reference)
            ax.axhline(y=breakout_level, color='orange', linestyle=':', linewidth=2,
                      alpha=0.7, label=f'Breakout: ₹{breakout_level:.0f}')
        
        # Moving averages
        if len(data) > 20:
            ma20 = data['close'].rolling(20, min_periods=1).mean()
            ax.plot(range(len(data)), ma20, '--', alpha=0.7, color='orange', linewidth=2, label='MA20')
        
        if len(data) > 50:
            ma50 = data['close'].rolling(50, min_periods=1).mean()
            ax.plot(range(len(data)), ma50, '--', alpha=0.7, color='purple', linewidth=2, label='MA50')
        
        # Current price with stage indicator
        current_price = data['close'].iloc[-1]
        ma20_current = ma20.iloc[-1] if len(data) > 20 else current_price
        ma50_current = ma50.iloc[-1] if len(data) > 50 else current_price
        
        # Stage analysis
        if current_price > ma20_current > ma50_current:
            stage = "Stage 2 ⬆️"
            stage_color = 'green'
        elif current_price > ma50_current:
            stage = "Stage 1 ➡️"
            stage_color = 'blue'
        else:
            stage = "Stage 4 ⬇️"
            stage_color = 'red'
        
        ax.axhline(y=current_price, color=stage_color, linestyle='-.', linewidth=3,
                  alpha=0.8, label=f'Current: ₹{current_price:.0f} ({stage})')
        
        ax.set_ylabel('Price (₹)', fontsize=12, fontweight='bold')
        ax.legend(loc='upper left', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_title('Enhanced VCP Price Action with Breakout Analysis', fontsize=14, fontweight='bold')
    
    def _plot_enhanced_volume(self, ax, data, recent_contractions):
        """Enhanced volume with dry-up analysis"""
        
        # Volume bars
        colors = ['darkgreen' if close >= open_val else 'darkred' 
                 for close, open_val in zip(data['close'], data['open'])]
        
        x_positions = range(len(data))
        bars = ax.bar(x_positions, data['volume'], color=colors, alpha=0.6, width=0.6)
        
        # Volume MA
        vol_ma = data['volume'].rolling(10, min_periods=1).mean()
        ax.plot(x_positions, vol_ma, color='black', linewidth=3, label='Vol MA(10)', alpha=0.8)
        
        # Average volume line
        avg_volume = data['volume'].mean()
        ax.axhline(y=avg_volume, color='blue', linestyle=':', linewidth=2,
                  alpha=0.7, label=f'Avg: {avg_volume/1e6:.1f}M')
        
        # Volume dry-up analysis for each contraction
        contraction_colors = ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
        
        for i, contraction in enumerate(recent_contractions):
            color = contraction_colors[i % len(contraction_colors)]
            
            start_mask = data['date'] >= pd.to_datetime(contraction.start_date)
            end_mask = data['date'] <= pd.to_datetime(contraction.end_date)
            
            if start_mask.any() and end_mask.any():
                start_pos = data[start_mask].index[0]
                end_pos = data[end_mask].index[-1]
                ax.axvspan(start_pos, end_pos, alpha=0.15, color=color, zorder=1)
        
        # Format volume
        ax.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
        
        ax.set_ylabel('Volume', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_title('Volume Dry-Up Analysis (Should Decline in Contractions)', fontsize=12, fontweight='bold')
    
    def _plot_vcp_analysis(self, ax, recent_contractions):
        """VCP contraction analysis chart"""
        
        if not recent_contractions:
            ax.text(0.5, 0.5, 'No contractions to analyze', ha='center', va='center', transform=ax.transAxes)
            return
        
        # Analyze volume decline across contractions
        contractions = list(range(1, len(recent_contractions) + 1))
        durations = [(c.end_date - c.start_date).days for c in recent_contractions]
        
        # Plot contraction progression
        bars = ax.bar(contractions, durations, color=['lightcoral', 'lightgreen', 'lightblue', 'lightyellow', 'lightpink'][:len(contractions)], 
                     alpha=0.7, edgecolor='black')
        
        # Add duration labels
        for i, (bar, duration) in enumerate(zip(bars, durations)):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                   f'{duration}d', ha='center', va='bottom', fontweight='bold')
        
        ax.set_xlabel('Contraction Number', fontweight='bold')
        ax.set_ylabel('Duration (Days)', fontweight='bold')
        ax.set_title('VCP Contraction Pattern', fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Ideal pattern indicator
        if len(durations) >= 2:
            if all(durations[i] >= durations[i+1] for i in range(len(durations)-1)):
                pattern_quality = "✅ Ideal (Tightening)"
            else:
                pattern_quality = "⚠️ Mixed Pattern"
        else:
            pattern_quality = "📊 Single Contraction"
        
        ax.text(0.02, 0.98, pattern_quality, transform=ax.transAxes, 
               fontweight='bold', va='top', bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow'))
    
    def _plot_pattern_stats(self, ax, full_pattern, recent_contractions, data):
        """Pattern statistics and quality metrics"""
        
        ax.axis('off')  # Remove axes for text display
        
        # Calculate key metrics
        current_price = data['close'].iloc[-1]
        pattern_start_price = data['close'].iloc[0]
        price_change = ((current_price - pattern_start_price) / pattern_start_price) * 100
        
        avg_volume = data['volume'].mean()
        recent_volume = data['volume'].tail(5).mean()
        volume_trend = "Declining ⬇️" if recent_volume < avg_volume else "Increasing ⬆️"
        
        # Calculate trading levels
        if len(recent_contractions) > 0:
            # Get recent data for support/resistance
            first_recent = min(c.start_date for c in recent_contractions)
            last_recent = max(c.end_date for c in recent_contractions)
            recent_data = data[(data['date'] >= pd.to_datetime(first_recent)) & 
                              (data['date'] <= pd.to_datetime(last_recent))]
            
            if len(recent_data) > 0:
                resistance = recent_data['high'].max()
                support = recent_data['low'].min()
                entry_level = resistance * 1.02
                stop_loss = support * 0.98
                target_level = entry_level * 1.25
                risk_reward = (target_level - entry_level) / (entry_level - stop_loss)
            else:
                entry_level = stop_loss = target_level = risk_reward = 0
        else:
            entry_level = stop_loss = target_level = risk_reward = 0
        
        # Statistics text
        stats_text = f"""📊 VCP ANALYSIS SUMMARY
        
🎯 Pattern Quality: {full_pattern.quality_score:.1f}/100
📈 Price Change: {price_change:+.1f}%
⏱️ Total Contractions: {len(full_pattern.contractions)}
🔥 Recent Active: {len(recent_contractions)}
        
📊 VOLUME ANALYSIS
💧 Avg Volume: {avg_volume/1e6:.1f}M
📈 Recent Trend: {volume_trend}
        
🎯 VCP QUALITY INDICATORS
{'✅' if full_pattern.quality_score > 90 else '⚠️'} Pattern Score: {'Excellent' if full_pattern.quality_score > 90 else 'Good' if full_pattern.quality_score > 75 else 'Fair'}
{'✅' if len(recent_contractions) >= 3 else '⚠️'} Contractions: {'Sufficient' if len(recent_contractions) >= 3 else 'Limited'}
{'✅' if recent_volume < avg_volume else '⚠️'} Volume Dry-up: {'Confirmed' if recent_volume < avg_volume else 'Pending'}

💡 TRADING SIGNALS
🎯 Entry: ₹{entry_level:.0f} (above resistance)
🛑 Stop: ₹{stop_loss:.0f} (below support)
📈 Target: ₹{target_level:.0f} ({((target_level/entry_level-1)*100):.0f}% gain)
⚖️ Risk:Reward = 1:{risk_reward:.1f}
💰 Position Size: 2% risk of capital"""
        
        ax.text(0.05, 0.95, stats_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', fontfamily='monospace',
               bbox=dict(boxstyle="round,pad=0.5", facecolor='lightcyan', alpha=0.8))
    
    def _format_trading_axis(self, ax, data):
        """Format x-axis for trading days"""
        
        ax.set_xlim(-0.5, len(data) - 0.5)
        
        # Custom tick spacing
        trading_days = len(data)
        if trading_days <= 30:
            tick_interval = 5
        elif trading_days <= 60:
            tick_interval = 10
        else:
            tick_interval = 15
        
        tick_positions = list(range(0, len(data), tick_interval))
        if tick_positions[-1] != len(data) - 1:
            tick_positions.append(len(data) - 1)
        
        tick_labels = [data.iloc[pos]['date'].strftime('%b %d') for pos in tick_positions]
        
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45)
        ax.grid(True, alpha=0.3, axis='x')

def main():
    """Create enhanced VCP charts"""
    
    print("📊 CREATING ENHANCED VCP CHARTS")
    print("=" * 50)
    print("Features: Volume Dry-up + Breakout Zones + Stage Analysis + Trading Stats")
    
    symbols = ['CIPLA', 'HDFCBANK', 'BAJAJFINSV']
    
    chart_creator = EnhancedVCPCharts()
    created_charts = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] Creating enhanced chart for {symbol}")
        print("-" * 40)
        
        chart_path = chart_creator.create_enhanced_vcp_chart(symbol)
        
        if chart_path:
            created_charts.append((symbol, chart_path))
            print(f"✅ SUCCESS: {chart_path}")
        else:
            print(f"❌ FAILED: No chart created")
    
    print(f"\n📊 ENHANCED CHART CREATION COMPLETE!")
    print(f"Successfully created {len(created_charts)}/{len(symbols)} charts")
    
    if created_charts:
        print(f"\n✅ ENHANCED CHARTS CREATED:")
        for symbol, path in created_charts:
            print(f"   🚀 {symbol:<12} → {path}")
        
        print(f"\n💡 ENHANCED FEATURES ADDED:")
        print(f"   📉 Volume dry-up analysis in contractions")
        print(f"   🎯 Clear breakout zones above resistance")
        print(f"   📈 Stage analysis (1,2,3,4) with indicators")
        print(f"   📊 Contraction pattern progression analysis")
        print(f"   🎯 Trading signals (entry, stop, target)")
        print(f"   📋 Comprehensive pattern statistics")

if __name__ == "__main__":
    main()