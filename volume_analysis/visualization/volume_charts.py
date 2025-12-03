"""
Volume Charts
=============

Create multi-pane charts for volume analysis visualization.

Features:
- Price with candlesticks or line
- Volume bars (colored by price direction)
- OBV overlay
- A/D Line overlay
- CMF histogram
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Tuple
from datetime import datetime
import logging
import os

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.gridspec import GridSpec
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    
try:
    import mplfinance as mpf
    HAS_MPLFINANCE = True
except ImportError:
    HAS_MPLFINANCE = False

from ..core.volume_indicators import VolumeIndicators
from ..analysis.accumulation_detector import AccumulationDetector, AccumulationSignal, PhaseType

logger = logging.getLogger(__name__)


class VolumeChartGenerator:
    """
    Generate volume analysis charts.
    
    Creates multi-pane charts showing:
    - Price action (candlestick or line)
    - Volume bars with color coding
    - OBV indicator
    - A/D Line indicator
    - CMF histogram
    """
    
    def __init__(self, style: str = 'dark'):
        """
        Initialize chart generator.
        
        Args:
            style: Chart style ('dark' or 'light')
        """
        self.style = style
        self.volume_indicators = VolumeIndicators()
        self.detector = AccumulationDetector()
        
        # Color scheme
        if style == 'dark':
            self.colors = {
                'background': '#1e1e1e',
                'text': '#ffffff',
                'grid': '#333333',
                'up': '#00ff88',
                'down': '#ff4444',
                'volume_up': '#00ff8866',
                'volume_down': '#ff444466',
                'obv': '#00bfff',
                'ad_line': '#ffaa00',
                'cmf_positive': '#00ff88',
                'cmf_negative': '#ff4444',
                'neutral': '#888888',
            }
        else:
            self.colors = {
                'background': '#ffffff',
                'text': '#000000',
                'grid': '#dddddd',
                'up': '#00aa00',
                'down': '#cc0000',
                'volume_up': '#00aa0066',
                'volume_down': '#cc000066',
                'obv': '#0066cc',
                'ad_line': '#cc6600',
                'cmf_positive': '#00aa00',
                'cmf_negative': '#cc0000',
                'neutral': '#666666',
            }
    
    def create_volume_analysis_chart(self, 
                                     df: pd.DataFrame,
                                     symbol: str = "Stock",
                                     signal: AccumulationSignal = None,
                                     save_path: str = None,
                                     show: bool = True,
                                     figsize: Tuple[int, int] = (14, 12)) -> Optional[plt.Figure]:
        """
        Create a comprehensive volume analysis chart.
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol for title
            signal: Optional AccumulationSignal with analysis results
            save_path: Path to save chart image
            show: Whether to display the chart
            figsize: Figure size (width, height)
            
        Returns:
            matplotlib Figure object or None
        """
        if not HAS_MATPLOTLIB:
            logger.error("matplotlib not installed. Run: pip install matplotlib")
            return None
        
        # Calculate indicators
        data = self.volume_indicators.calculate_all(df)
        data = self.volume_indicators.detect_volume_dryup(data)
        data = self.volume_indicators.detect_volume_surge(data)
        
        # Get analysis if not provided
        if signal is None:
            signal = self.detector.analyze(df, symbol)
        
        # Set style
        if self.style == 'dark':
            plt.style.use('dark_background')
        else:
            plt.style.use('default')
        
        # Create figure with GridSpec
        fig = plt.figure(figsize=figsize, facecolor=self.colors['background'])
        gs = GridSpec(5, 1, height_ratios=[3, 1, 1, 1, 0.8], hspace=0.05)
        
        # Ensure date column is datetime
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
            x_data = data['date']
        else:
            x_data = data.index
        
        # =====================================
        # Panel 1: Price (Candlestick or Line)
        # =====================================
        ax1 = fig.add_subplot(gs[0])
        
        # Draw candlesticks manually
        width = 0.6
        for idx in range(len(data)):
            row = data.iloc[idx]
            x = mdates.date2num(x_data.iloc[idx]) if isinstance(x_data.iloc[idx], datetime) else idx
            
            # Determine color
            if row['close'] >= row['open']:
                color = self.colors['up']
                body_bottom = row['open']
            else:
                color = self.colors['down']
                body_bottom = row['close']
            
            body_height = abs(row['close'] - row['open'])
            
            # Draw wick (high-low line)
            ax1.plot([x, x], [row['low'], row['high']], color=color, linewidth=0.8)
            
            # Draw body
            ax1.bar(x, body_height, width=width, bottom=body_bottom, color=color, edgecolor=color)
        
        # Add moving averages if available
        if 'close' in data.columns:
            ma20 = data['close'].rolling(20).mean()
            ma50 = data['close'].rolling(50).mean()
            x_vals = mdates.date2num(x_data) if isinstance(x_data.iloc[0], datetime) else range(len(data))
            ax1.plot(x_vals, ma20, color='#ffaa00', linewidth=1, label='MA20', alpha=0.7)
            ax1.plot(x_vals, ma50, color='#00aaff', linewidth=1, label='MA50', alpha=0.7)
        
        # Title with signal info
        phase_color = self.colors['up'] if signal.phase == PhaseType.ACCUMULATION else \
                      self.colors['down'] if signal.phase == PhaseType.DISTRIBUTION else \
                      self.colors['neutral']
        
        title = f"{symbol} - Volume Analysis | {signal.phase.value.upper()} (Score: {signal.score:.1f})"
        ax1.set_title(title, fontsize=14, fontweight='bold', color=phase_color)
        
        ax1.set_ylabel('Price', fontsize=10, color=self.colors['text'])
        ax1.grid(True, alpha=0.3, color=self.colors['grid'])
        ax1.legend(loc='upper left', fontsize=8)
        ax1.tick_params(labelbottom=False)
        
        # =====================================
        # Panel 2: Volume Bars
        # =====================================
        ax2 = fig.add_subplot(gs[1], sharex=ax1)
        
        # Color volume bars by price direction
        colors = []
        for idx in range(len(data)):
            row = data.iloc[idx]
            if row['close'] >= row['open']:
                colors.append(self.colors['volume_up'])
            else:
                colors.append(self.colors['volume_down'])
        
        x_vals = mdates.date2num(x_data) if isinstance(x_data.iloc[0], datetime) else range(len(data))
        ax2.bar(x_vals, data['volume'], color=colors, width=0.8)
        
        # Volume SMA
        if 'volume_sma_20' in data.columns:
            ax2.plot(x_vals, data['volume_sma_20'], color='#ffaa00', linewidth=1, label='Vol MA20')
        
        ax2.set_ylabel('Volume', fontsize=10, color=self.colors['text'])
        ax2.grid(True, alpha=0.3, color=self.colors['grid'])
        ax2.tick_params(labelbottom=False)
        ax2.legend(loc='upper left', fontsize=8)
        
        # Format y-axis for volume (millions/lakhs)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M'))
        
        # =====================================
        # Panel 3: OBV
        # =====================================
        ax3 = fig.add_subplot(gs[2], sharex=ax1)
        
        ax3.plot(x_vals, data['obv'], color=self.colors['obv'], linewidth=1.5, label='OBV')
        if 'obv_sma_20' in data.columns:
            ax3.plot(x_vals, data['obv_sma_20'], color='#ffaa00', linewidth=1, label='OBV MA20', linestyle='--')
        
        # Fill area between OBV and its SMA
        if 'obv_sma_20' in data.columns:
            ax3.fill_between(x_vals, data['obv'], data['obv_sma_20'],
                            where=(data['obv'] >= data['obv_sma_20']),
                            color=self.colors['up'], alpha=0.3)
            ax3.fill_between(x_vals, data['obv'], data['obv_sma_20'],
                            where=(data['obv'] < data['obv_sma_20']),
                            color=self.colors['down'], alpha=0.3)
        
        ax3.set_ylabel('OBV', fontsize=10, color=self.colors['text'])
        ax3.grid(True, alpha=0.3, color=self.colors['grid'])
        ax3.tick_params(labelbottom=False)
        ax3.legend(loc='upper left', fontsize=8)
        
        # =====================================
        # Panel 4: A/D Line
        # =====================================
        ax4 = fig.add_subplot(gs[3], sharex=ax1)
        
        ax4.plot(x_vals, data['ad_line'], color=self.colors['ad_line'], linewidth=1.5, label='A/D Line')
        if 'ad_line_sma_20' in data.columns:
            ax4.plot(x_vals, data['ad_line_sma_20'], color='#888888', linewidth=1, label='A/D MA20', linestyle='--')
        
        # Fill
        if 'ad_line_sma_20' in data.columns:
            ax4.fill_between(x_vals, data['ad_line'], data['ad_line_sma_20'],
                            where=(data['ad_line'] >= data['ad_line_sma_20']),
                            color=self.colors['up'], alpha=0.3)
            ax4.fill_between(x_vals, data['ad_line'], data['ad_line_sma_20'],
                            where=(data['ad_line'] < data['ad_line_sma_20']),
                            color=self.colors['down'], alpha=0.3)
        
        ax4.set_ylabel('A/D Line', fontsize=10, color=self.colors['text'])
        ax4.grid(True, alpha=0.3, color=self.colors['grid'])
        ax4.tick_params(labelbottom=False)
        ax4.legend(loc='upper left', fontsize=8)
        
        # =====================================
        # Panel 5: CMF Histogram
        # =====================================
        ax5 = fig.add_subplot(gs[4], sharex=ax1)
        
        cmf_colors = [self.colors['cmf_positive'] if v >= 0 else self.colors['cmf_negative'] 
                      for v in data['cmf']]
        ax5.bar(x_vals, data['cmf'], color=cmf_colors, width=0.8)
        ax5.axhline(y=0, color=self.colors['neutral'], linewidth=0.5)
        ax5.axhline(y=0.25, color=self.colors['up'], linewidth=0.5, linestyle='--', alpha=0.5)
        ax5.axhline(y=-0.25, color=self.colors['down'], linewidth=0.5, linestyle='--', alpha=0.5)
        
        ax5.set_ylabel('CMF', fontsize=10, color=self.colors['text'])
        ax5.set_ylim(-0.5, 0.5)
        ax5.grid(True, alpha=0.3, color=self.colors['grid'])
        
        # Format x-axis
        if isinstance(x_data.iloc[0], datetime):
            ax5.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            ax5.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            plt.xticks(rotation=45)
        
        ax5.set_xlabel('Date', fontsize=10, color=self.colors['text'])
        
        # =====================================
        # Add Analysis Summary Box
        # =====================================
        summary_text = (
            f"📊 Analysis Summary\n"
            f"Phase: {signal.phase.value.upper()}\n"
            f"Strength: {signal.strength.value}\n"
            f"Score: {signal.score:.1f}/100\n"
            f"─────────────\n"
            f"OBV: {signal.obv_score:.0f}  A/D: {signal.ad_score:.0f}\n"
            f"CMF: {signal.cmf_score:.0f}  Vol: {signal.volume_score:.0f}"
        )
        
        # Position box in upper right of price panel
        props = dict(boxstyle='round', facecolor=self.colors['background'], 
                    edgecolor=phase_color, alpha=0.9)
        ax1.text(0.98, 0.98, summary_text, transform=ax1.transAxes, fontsize=9,
                verticalalignment='top', horizontalalignment='right',
                bbox=props, color=self.colors['text'], family='monospace')
        
        plt.tight_layout()
        
        # Save if path provided
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight',
                       facecolor=self.colors['background'])
            logger.info(f"Chart saved to {save_path}")
        
        if show:
            plt.show()
        
        return fig
    
    def create_comparison_chart(self,
                               signals: List[AccumulationSignal],
                               title: str = "Accumulation vs Distribution",
                               save_path: str = None,
                               show: bool = True) -> Optional[plt.Figure]:
        """
        Create a comparison chart showing multiple stocks' scores.
        
        Args:
            signals: List of AccumulationSignal objects
            title: Chart title
            save_path: Path to save chart
            show: Whether to display
            
        Returns:
            matplotlib Figure or None
        """
        if not HAS_MATPLOTLIB:
            return None
        
        if not signals:
            return None
        
        # Set style
        if self.style == 'dark':
            plt.style.use('dark_background')
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 8), facecolor=self.colors['background'])
        
        # Separate by phase
        acc_signals = [s for s in signals if s.phase == PhaseType.ACCUMULATION]
        dist_signals = [s for s in signals if s.phase == PhaseType.DISTRIBUTION]
        
        # Sort by score
        acc_signals.sort(key=lambda x: x.score, reverse=True)
        dist_signals.sort(key=lambda x: x.score)
        
        # Limit to top 15 each
        acc_signals = acc_signals[:15]
        dist_signals = dist_signals[:15]
        
        # =====================================
        # Left: Accumulation
        # =====================================
        ax1 = axes[0]
        
        if acc_signals:
            symbols = [s.symbol.replace('.NS', '') for s in acc_signals]
            scores = [s.score for s in acc_signals]
            
            colors = [self.colors['up'] if s.strength.value == 'strong' else 
                     '#88ff88' if s.strength.value == 'moderate' else '#aaffaa'
                     for s in acc_signals]
            
            bars = ax1.barh(range(len(symbols)), scores, color=colors)
            ax1.set_yticks(range(len(symbols)))
            ax1.set_yticklabels(symbols, fontsize=9)
            ax1.set_xlim(50, 100)
            ax1.axvline(x=75, color=self.colors['neutral'], linestyle='--', alpha=0.5)
            ax1.axvline(x=65, color=self.colors['neutral'], linestyle=':', alpha=0.5)
        
        ax1.set_title("🟢 TOP ACCUMULATION", fontsize=12, fontweight='bold', color=self.colors['up'])
        ax1.set_xlabel("Score", fontsize=10)
        ax1.grid(True, alpha=0.3, axis='x')
        ax1.invert_yaxis()
        
        # =====================================
        # Right: Distribution
        # =====================================
        ax2 = axes[1]
        
        if dist_signals:
            symbols = [s.symbol.replace('.NS', '') for s in dist_signals]
            scores = [s.score for s in dist_signals]
            
            colors = [self.colors['down'] if s.strength.value == 'strong' else 
                     '#ff8888' if s.strength.value == 'moderate' else '#ffaaaa'
                     for s in dist_signals]
            
            bars = ax2.barh(range(len(symbols)), scores, color=colors)
            ax2.set_yticks(range(len(symbols)))
            ax2.set_yticklabels(symbols, fontsize=9)
            ax2.set_xlim(0, 50)
            ax2.axvline(x=25, color=self.colors['neutral'], linestyle='--', alpha=0.5)
            ax2.axvline(x=35, color=self.colors['neutral'], linestyle=':', alpha=0.5)
        
        ax2.set_title("🔴 TOP DISTRIBUTION", fontsize=12, fontweight='bold', color=self.colors['down'])
        ax2.set_xlabel("Score", fontsize=10)
        ax2.grid(True, alpha=0.3, axis='x')
        ax2.invert_yaxis()
        
        fig.suptitle(title, fontsize=14, fontweight='bold', color=self.colors['text'])
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight',
                       facecolor=self.colors['background'])
        
        if show:
            plt.show()
        
        return fig
    
    def create_score_heatmap(self,
                            signals: List[AccumulationSignal],
                            save_path: str = None,
                            show: bool = True) -> Optional[plt.Figure]:
        """
        Create a heatmap showing component scores for multiple stocks.
        
        Args:
            signals: List of AccumulationSignal objects
            save_path: Path to save chart
            show: Whether to display
            
        Returns:
            matplotlib Figure or None
        """
        if not HAS_MATPLOTLIB:
            return None
        
        if not signals or len(signals) < 2:
            return None
        
        # Limit to top 20 by absolute deviation from 50
        signals = sorted(signals, key=lambda x: abs(x.score - 50), reverse=True)[:20]
        
        # Prepare data
        symbols = [s.symbol.replace('.NS', '') for s in signals]
        components = ['OBV', 'A/D', 'CMF', 'Volume', 'Price', 'Total']
        
        data = []
        for s in signals:
            data.append([s.obv_score, s.ad_score, s.cmf_score, 
                        s.volume_score, s.price_action_score, s.score])
        
        data = np.array(data)
        
        # Create figure
        if self.style == 'dark':
            plt.style.use('dark_background')
        
        fig, ax = plt.subplots(figsize=(10, 12), facecolor=self.colors['background'])
        
        # Create heatmap
        cmap = plt.cm.RdYlGn
        im = ax.imshow(data, cmap=cmap, aspect='auto', vmin=0, vmax=100)
        
        # Ticks
        ax.set_xticks(range(len(components)))
        ax.set_xticklabels(components, fontsize=10)
        ax.set_yticks(range(len(symbols)))
        ax.set_yticklabels(symbols, fontsize=9)
        
        # Add text annotations
        for i in range(len(symbols)):
            for j in range(len(components)):
                value = data[i, j]
                text_color = 'black' if 30 < value < 70 else 'white'
                ax.text(j, i, f'{value:.0f}', ha='center', va='center',
                       fontsize=8, color=text_color)
        
        # Colorbar
        cbar = plt.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label('Score', fontsize=10)
        
        ax.set_title("Volume Analysis Score Heatmap", fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight',
                       facecolor=self.colors['background'])
        
        if show:
            plt.show()
        
        return fig


def generate_report_charts(results, output_dir: str = "volume_charts") -> List[str]:
    """
    Generate charts for scan results.
    
    Args:
        results: ScanResults from VolumeScanner
        output_dir: Directory to save charts
        
    Returns:
        List of generated file paths
    """
    os.makedirs(output_dir, exist_ok=True)
    
    chart_gen = VolumeChartGenerator(style='dark')
    files = []
    
    # Comparison chart
    all_signals = results.accumulation + results.distribution
    if all_signals:
        path = os.path.join(output_dir, "comparison_chart.png")
        chart_gen.create_comparison_chart(all_signals, save_path=path, show=False)
        files.append(path)
    
    # Heatmap
    if len(all_signals) >= 2:
        path = os.path.join(output_dir, "score_heatmap.png")
        chart_gen.create_score_heatmap(all_signals, save_path=path, show=False)
        files.append(path)
    
    return files


if __name__ == "__main__":
    # Test chart generation
    import yfinance as yf
    
    print("Testing Volume Chart Generator...")
    
    # Download sample data
    ticker = yf.Ticker("RELIANCE.NS")
    df = ticker.history(period="6mo")
    
    # Rename columns
    df.columns = df.columns.str.lower()
    df = df.reset_index()
    df = df.rename(columns={'Date': 'date'})
    
    # Generate chart
    chart_gen = VolumeChartGenerator(style='dark')
    chart_gen.create_volume_analysis_chart(
        df, 
        symbol="RELIANCE",
        save_path="test_volume_chart.png",
        show=True
    )
