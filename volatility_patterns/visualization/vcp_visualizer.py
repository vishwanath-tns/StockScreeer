"""
VCP Pattern Visualization System
===============================

Advanced chart visualization system for VCP patterns with:
- Pattern detection overlays
- Technical indicator displays
- Volume analysis charts
- Stage analysis annotations
- Interactive features and export capabilities

Author: GitHub Copilot
Date: November 2025
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from datetime import date, timedelta, datetime
import seaborn as sns
from pathlib import Path

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from volatility_patterns.data.data_service import DataService
from volatility_patterns.core.vcp_detector import VCPDetector, VCPPattern, VCPContraction
from volatility_patterns.core.technical_indicators import TechnicalIndicators
from volatility_patterns.analysis.vcp_scanner import VCPScanner


class VCPVisualizer:
    """
    Advanced VCP Pattern Visualization Engine
    
    Creates comprehensive charts showing:
    - Price action with pattern overlays
    - Volume analysis
    - Technical indicators
    - Pattern annotations
    - Stage analysis
    """
    
    def __init__(self, figsize: Tuple[int, int] = (16, 12)):
        self.data_service = DataService()
        self.detector = VCPDetector()
        self.indicators = TechnicalIndicators()
        self.scanner = VCPScanner()
        self.figsize = figsize
        
        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette("husl")
    
    def create_vcp_chart(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        pattern: Optional[VCPPattern] = None,
        save_path: Optional[str] = None,
        show_chart: bool = True
    ) -> plt.Figure:
        """
        Create comprehensive VCP pattern chart
        
        Args:
            symbol: Stock symbol
            start_date: Chart start date
            end_date: Chart end date  
            pattern: VCP pattern to highlight (optional)
            save_path: Path to save chart (optional)
            show_chart: Whether to display chart
            
        Returns:
            Matplotlib figure object
        """
        # Get data
        data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
        if len(data) < 50:
            raise ValueError(f"Insufficient data for {symbol}")
        
        # Calculate indicators
        data_with_indicators = self._prepare_data(data)
        
        # Detect pattern if not provided
        if pattern is None:
            patterns = self.detector.detect_vcp_patterns(
                data_with_indicators, symbol, lookback_days=len(data)
            )
            if patterns:
                pattern = max(patterns, key=lambda p: p.quality_score)
        
        # Create figure with subplots
        fig, axes = plt.subplots(4, 1, figsize=self.figsize, 
                                gridspec_kw={'height_ratios': [3, 1, 1, 0.8]})
        fig.suptitle(f'{symbol} - VCP Pattern Analysis', fontsize=16, fontweight='bold')
        
        # Main price chart
        self._plot_price_chart(axes[0], data_with_indicators, pattern, symbol)
        
        # Volume chart
        self._plot_volume_chart(axes[1], data_with_indicators, pattern)
        
        # Technical indicators
        self._plot_technical_indicators(axes[2], data_with_indicators)
        
        # Pattern summary
        self._plot_pattern_summary(axes[3], pattern, symbol)
        
        # Format dates
        for ax in axes[:-1]:  # Skip summary subplot
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Save if requested
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Chart saved to {save_path}")
        
        # Show if requested
        if show_chart:
            plt.show()
        
        return fig
    
    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare data with all required indicators"""
        result = data.copy()
        
        # Calculate technical indicators
        result = self.indicators.calculate_atr(result, period=14)
        result = self.indicators.calculate_bollinger_bands(result, period=20)
        result = self.indicators.calculate_volume_ma(result, period=20)
        result = self.indicators.calculate_volume_ma(result, period=50)
        result = self.indicators.calculate_price_range_compression(result, period=20)
        result = self.indicators.detect_bollinger_squeeze(result)
        
        # Add moving averages
        result['sma_20'] = result['close'].rolling(20).mean()
        result['sma_50'] = result['close'].rolling(50).mean()
        result['sma_150'] = result['close'].rolling(150).mean()
        result['sma_200'] = result['close'].rolling(200).mean()
        
        return result
    
    def _plot_price_chart(self, ax, data: pd.DataFrame, pattern: Optional[VCPPattern], symbol: str):
        """Plot main price chart with pattern overlays"""
        dates = pd.to_datetime(data['date'])
        
        # Plot candlesticks (simplified as OHLC bars)
        for i in range(len(data)):
            color = 'green' if data.iloc[i]['close'] >= data.iloc[i]['open'] else 'red'
            alpha = 0.7
            
            # High-low line
            ax.plot([dates.iloc[i], dates.iloc[i]], 
                   [data.iloc[i]['low'], data.iloc[i]['high']], 
                   color=color, linewidth=1, alpha=alpha)
            
            # Open-close body
            body_height = abs(data.iloc[i]['close'] - data.iloc[i]['open'])
            body_bottom = min(data.iloc[i]['close'], data.iloc[i]['open'])
            
            rect = Rectangle((dates.iloc[i] - timedelta(hours=6), body_bottom),
                           timedelta(hours=12), body_height,
                           facecolor=color, alpha=alpha)
            ax.add_patch(rect)
        
        # Plot moving averages
        ax.plot(dates, data['sma_20'], label='SMA 20', color='orange', linewidth=1)
        ax.plot(dates, data['sma_50'], label='SMA 50', color='blue', linewidth=1.5)
        ax.plot(dates, data['sma_150'], label='SMA 150', color='purple', linewidth=1.5)
        ax.plot(dates, data['sma_200'], label='SMA 200', color='red', linewidth=2)
        
        # Plot Bollinger Bands
        if 'bb_upper_20' in data.columns:
            ax.fill_between(dates, data['bb_lower_20'], data['bb_upper_20'], 
                           alpha=0.2, color='gray', label='Bollinger Bands')
        
        # Highlight VCP pattern if available
        if pattern:
            self._highlight_vcp_pattern(ax, data, pattern)
        
        ax.set_title(f'{symbol} - Price Action & VCP Pattern', fontsize=14)
        ax.set_ylabel('Price (Rs)', fontsize=12)
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
    
    def _highlight_vcp_pattern(self, ax, data: pd.DataFrame, pattern: VCPPattern):
        """Highlight VCP pattern on price chart"""
        dates = pd.to_datetime(data['date'])
        
        # Find pattern date range in data
        pattern_start = pd.to_datetime(pattern.pattern_start)
        pattern_end = pd.to_datetime(pattern.pattern_end)
        
        # Highlight pattern base
        pattern_mask = (dates >= pattern_start) & (dates <= pattern_end)
        if pattern_mask.any():
            pattern_data = data[pattern_mask]
            pattern_dates = dates[pattern_mask]
            
            # Draw pattern box
            y_min = pattern_data['low'].min()
            y_max = pattern_data['high'].max()
            
            rect = patches.Rectangle(
                (pattern_start, y_min), 
                pattern_end - pattern_start,
                y_max - y_min,
                linewidth=2, 
                edgecolor='yellow', 
                facecolor='yellow',
                alpha=0.2,
                label=f'VCP Pattern (Q: {pattern.quality_score:.1f})'
            )
            ax.add_patch(rect)
            
            # Mark contractions
            for i, contraction in enumerate(pattern.contractions):
                cont_start = pd.to_datetime(contraction.start_date)
                cont_end = pd.to_datetime(contraction.end_date)
                
                # Find contraction data points
                cont_mask = (dates >= cont_start) & (dates <= cont_end)
                if cont_mask.any():
                    cont_data = data[cont_mask]
                    cont_y_min = cont_data['low'].min()
                    cont_y_max = cont_data['high'].max()
                    
                    # Color-code contractions (tighter = greener)
                    colors = ['red', 'orange', 'yellow', 'lightgreen', 'green']
                    color_idx = min(i, len(colors) - 1)
                    
                    cont_rect = patches.Rectangle(
                        (cont_start, cont_y_min),
                        cont_end - cont_start,
                        cont_y_max - cont_y_min,
                        linewidth=1,
                        edgecolor=colors[color_idx],
                        facecolor='none',
                        linestyle='--'
                    )
                    ax.add_patch(cont_rect)
            
            # Mark breakout level if setup is complete
            if pattern.is_setup_complete:
                ax.axhline(y=pattern.breakout_level, color='green', 
                          linestyle='--', linewidth=2, 
                          label=f'Breakout: Rs {pattern.breakout_level:.1f}')
                ax.axhline(y=pattern.stop_loss_level, color='red',
                          linestyle='--', linewidth=2,
                          label=f'Stop Loss: Rs {pattern.stop_loss_level:.1f}')
    
    def _plot_volume_chart(self, ax, data: pd.DataFrame, pattern: Optional[VCPPattern]):
        """Plot volume chart with VCP volume analysis"""
        dates = pd.to_datetime(data['date'])
        
        # Volume bars
        colors = ['green' if data.iloc[i]['close'] >= data.iloc[i]['open'] 
                 else 'red' for i in range(len(data))]
        ax.bar(dates, data['volume'], color=colors, alpha=0.7)
        
        # Volume moving averages
        if 'vol_ma_20' in data.columns:
            ax.plot(dates, data['vol_ma_20'], label='Vol MA 20', color='orange', linewidth=2)
        if 'vol_ma_50' in data.columns:
            ax.plot(dates, data['vol_ma_50'], label='Vol MA 50', color='blue', linewidth=2)
        
        # Highlight volume dry-up during pattern
        if pattern:
            pattern_start = pd.to_datetime(pattern.pattern_start)
            pattern_end = pd.to_datetime(pattern.pattern_end)
            pattern_mask = (dates >= pattern_start) & (dates <= pattern_end)
            
            if pattern_mask.any():
                # Highlight reduced volume during pattern
                ax.fill_between(dates[pattern_mask], 0, data['volume'][pattern_mask],
                              alpha=0.3, color='yellow', 
                              label='Pattern Volume')
        
        ax.set_title('Volume Analysis - VCP Volume Dry-up', fontsize=12)
        ax.set_ylabel('Volume', fontsize=10)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
    
    def _plot_technical_indicators(self, ax, data: pd.DataFrame):
        """Plot technical indicators relevant to VCP"""
        dates = pd.to_datetime(data['date'])
        
        # ATR percentage
        if 'atr_14_pct' in data.columns:
            ax.plot(dates, data['atr_14_pct'], label='ATR 14%', color='red', linewidth=1.5)
        
        # Bollinger Band width
        if 'bb_width_20' in data.columns:
            ax.plot(dates, data['bb_width_20'], label='BB Width', color='blue', linewidth=1.5)
        
        # Range compression
        if 'range_compression_20' in data.columns:
            ax.plot(dates, data['range_compression_20'], 
                   label='Range Compression', color='green', linewidth=1.5)
        
        # Squeeze indicator
        if 'bb_squeeze' in data.columns:
            squeeze_dates = dates[data['bb_squeeze']]
            if len(squeeze_dates) > 0:
                ax.scatter(squeeze_dates, [5] * len(squeeze_dates),
                          color='yellow', marker='s', s=30,
                          label='BB Squeeze', alpha=0.8)
        
        ax.set_title('Technical Indicators - Volatility Compression', fontsize=12)
        ax.set_ylabel('Percentage / Ratio', fontsize=10)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 15)  # Reasonable range for indicators
    
    def _plot_pattern_summary(self, ax, pattern: Optional[VCPPattern], symbol: str):
        """Plot pattern summary information"""
        ax.axis('off')
        
        if pattern:
            # Create summary text
            summary_text = f"""
Pattern Quality Score: {pattern.quality_score:.1f}/100
Pattern Duration: {pattern.base_duration} days
Contractions: {len(pattern.contractions)}
Volatility Compression: {pattern.volatility_compression:.2f}x
Volume Compression: {pattern.volume_compression:.2f}x
Current Stage: {pattern.current_stage}
Setup Complete: {'Yes' if pattern.is_setup_complete else 'No'}
Total Decline: {pattern.total_decline:.1f}%
            """.strip()
            
            if pattern.is_setup_complete:
                summary_text += f"\nBreakout Level: Rs {pattern.breakout_level:.1f}"
                summary_text += f"\nStop Loss: Rs {pattern.stop_loss_level:.1f}"
                summary_text += f"\nRisk/Reward: {((pattern.breakout_level - pattern.stop_loss_level) / pattern.stop_loss_level * 100):.1f}%"
            
            # Quality color coding
            if pattern.quality_score >= 80:
                quality_color = 'green'
                quality_label = 'Excellent'
            elif pattern.quality_score >= 60:
                quality_color = 'orange'
                quality_label = 'Good'
            else:
                quality_color = 'red'
                quality_label = 'Fair'
            
            summary_text += f"\nQuality Rating: {quality_label}"
            
            ax.text(0.05, 0.95, summary_text, transform=ax.transAxes,
                   fontsize=11, verticalalignment='top',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor=quality_color, alpha=0.2))
        else:
            ax.text(0.05, 0.5, f"No VCP pattern detected for {symbol}\nin the selected timeframe",
                   transform=ax.transAxes, fontsize=12,
                   bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgray', alpha=0.3))
    
    def create_pattern_comparison_chart(
        self,
        patterns_data: List[Tuple[str, VCPPattern]],
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Create comparison chart for multiple VCP patterns
        
        Args:
            patterns_data: List of (symbol, pattern) tuples
            save_path: Optional save path
            
        Returns:
            Matplotlib figure
        """
        n_patterns = len(patterns_data)
        if n_patterns == 0:
            raise ValueError("No patterns provided")
        
        # Create subplot grid
        cols = min(3, n_patterns)
        rows = (n_patterns + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 5, rows * 4))
        fig.suptitle('VCP Pattern Comparison', fontsize=16, fontweight='bold')
        
        if n_patterns == 1:
            axes = [axes]
        elif rows == 1:
            axes = [axes] if n_patterns == 1 else list(axes)
        else:
            axes = [ax for row in axes for ax in row]
        
        for i, (symbol, pattern) in enumerate(patterns_data):
            if i >= len(axes):
                break
            
            ax = axes[i]
            
            # Get data for pattern
            start_date = pattern.pattern_start - timedelta(days=30)
            end_date = pattern.pattern_end + timedelta(days=30)
            
            try:
                data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
                data_with_indicators = self._prepare_data(data)
                
                # Simplified price plot
                dates = pd.to_datetime(data_with_indicators['date'])
                ax.plot(dates, data_with_indicators['close'], linewidth=1.5)
                
                # Highlight pattern
                pattern_start = pd.to_datetime(pattern.pattern_start)
                pattern_end = pd.to_datetime(pattern.pattern_end)
                pattern_mask = (dates >= pattern_start) & (dates <= pattern_end)
                
                if pattern_mask.any():
                    pattern_data = data_with_indicators[pattern_mask]
                    y_min = pattern_data['low'].min()
                    y_max = pattern_data['high'].max()
                    
                    rect = patches.Rectangle(
                        (pattern_start, y_min),
                        pattern_end - pattern_start,
                        y_max - y_min,
                        alpha=0.3, facecolor='yellow', edgecolor='orange'
                    )
                    ax.add_patch(rect)
                
                ax.set_title(f'{symbol} (Q: {pattern.quality_score:.1f})', fontsize=12)
                ax.grid(True, alpha=0.3)
                
            except Exception as e:
                ax.text(0.5, 0.5, f'Error loading\n{symbol}', 
                       transform=ax.transAxes, ha='center', va='center')
        
        # Hide unused subplots
        for i in range(n_patterns, len(axes)):
            axes[i].axis('off')
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def create_pattern_dashboard(
        self,
        symbol: str,
        lookback_days: int = 365,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Create comprehensive VCP pattern dashboard
        
        Args:
            symbol: Stock symbol to analyze
            lookback_days: Days of historical data
            save_path: Optional save path
            
        Returns:
            Dashboard figure
        """
        # Get data
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)
        
        data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
        if len(data) < 100:
            raise ValueError(f"Insufficient data for {symbol}")
        
        # Detect patterns
        patterns = self.detector.detect_vcp_patterns(data, symbol, lookback_days)
        best_pattern = max(patterns, key=lambda p: p.quality_score) if patterns else None
        
        # Create dashboard
        fig = self.create_vcp_chart(symbol, start_date, end_date, best_pattern, 
                                  save_path, show_chart=False)
        
        return fig
    
    def export_pattern_report(
        self,
        symbol: str,
        pattern: VCPPattern,
        output_dir: str = "vcp_reports"
    ):
        """Export comprehensive pattern analysis report"""
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        # Generate chart
        start_date = pattern.pattern_start - timedelta(days=60)
        end_date = date.today()
        
        chart_path = f"{output_dir}/{symbol}_vcp_analysis.png"
        fig = self.create_vcp_chart(symbol, start_date, end_date, pattern, chart_path, False)
        
        # Generate text report
        report_path = f"{output_dir}/{symbol}_vcp_report.txt"
        with open(report_path, 'w') as f:
            f.write(f"VCP PATTERN ANALYSIS REPORT\n")
            f.write(f"{'=' * 40}\n\n")
            f.write(f"Symbol: {symbol}\n")
            f.write(f"Analysis Date: {date.today()}\n\n")
            f.write(f"PATTERN DETAILS\n")
            f.write(f"Quality Score: {pattern.quality_score:.1f}/100\n")
            f.write(f"Pattern Duration: {pattern.base_duration} days\n")
            f.write(f"Contractions: {len(pattern.contractions)}\n")
            f.write(f"Volatility Compression: {pattern.volatility_compression:.2f}x\n")
            f.write(f"Volume Compression: {pattern.volume_compression:.2f}x\n")
            f.write(f"Current Stage: {pattern.current_stage}\n")
            f.write(f"Setup Complete: {'Yes' if pattern.is_setup_complete else 'No'}\n\n")
            
            if pattern.is_setup_complete:
                f.write(f"TRADING LEVELS\n")
                f.write(f"Breakout Level: Rs {pattern.breakout_level:.2f}\n")
                f.write(f"Stop Loss Level: Rs {pattern.stop_loss_level:.2f}\n")
                f.write(f"Risk/Reward Ratio: {((pattern.breakout_level - pattern.stop_loss_level) / pattern.stop_loss_level * 100):.1f}%\n\n")
            
            f.write(f"Chart saved to: {chart_path}\n")
        
        print(f"Pattern report exported to {output_dir}")
        return report_path, chart_path