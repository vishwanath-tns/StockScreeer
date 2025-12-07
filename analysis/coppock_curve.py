#!/usr/bin/env python3
"""
Coppock Curve Indicator for Nifty 50
====================================
The Coppock Curve is a long-term momentum indicator developed by Edwin Coppock.
It's calculated as a 10-period WMA of the sum of 14-period ROC and 11-period ROC.

Traditional Settings (Monthly):
- ROC1: 14 periods (months)
- ROC2: 11 periods (months)
- WMA: 10 periods

Buy Signal: When Coppock turns up from below zero
Sell Signal: When Coppock turns down from above zero (less reliable)

This tool supports both Monthly and Weekly timeframes.
It fetches data directly from Yahoo Finance for indices.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Tuple
import threading

from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

# Try to import yfinance
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.dates as mdates

load_dotenv()


def get_engine():
    """Create database engine."""
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = os.getenv('MYSQL_PORT', '3306')
    db = os.getenv('MYSQL_DB', 'marketdata')
    user = os.getenv('MYSQL_USER', 'root')
    pwd = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
    
    return create_engine(
        f'mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}',
        pool_pre_ping=True,
        pool_recycle=3600
    )


def calculate_wma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Weighted Moving Average."""
    weights = np.arange(1, period + 1)
    
    def wma(x):
        return np.sum(weights * x) / weights.sum()
    
    return series.rolling(window=period).apply(wma, raw=True)


def calculate_coppock_curve(df: pd.DataFrame, 
                            roc1_period: int = 14, 
                            roc2_period: int = 11, 
                            wma_period: int = 10) -> pd.DataFrame:
    """
    Calculate Coppock Curve.
    
    Formula:
    Coppock = WMA(ROC1 + ROC2, WMA_period)
    
    Where:
    - ROC1 = Rate of Change over roc1_period
    - ROC2 = Rate of Change over roc2_period
    - WMA = Weighted Moving Average
    """
    df = df.copy()
    
    # Calculate Rate of Change
    df['ROC1'] = ((df['close'] - df['close'].shift(roc1_period)) / df['close'].shift(roc1_period)) * 100
    df['ROC2'] = ((df['close'] - df['close'].shift(roc2_period)) / df['close'].shift(roc2_period)) * 100
    
    # Sum of ROCs
    df['ROC_Sum'] = df['ROC1'] + df['ROC2']
    
    # Weighted Moving Average of ROC Sum
    df['Coppock'] = calculate_wma(df['ROC_Sum'], wma_period)
    
    # Signal: Coppock turning up from below zero
    df['Coppock_Prev'] = df['Coppock'].shift(1)
    df['Signal'] = 'None'
    
    # Buy signal: Coppock crosses above its previous value while below zero
    buy_condition = (df['Coppock'] > df['Coppock_Prev']) & (df['Coppock_Prev'] < 0) & (df['Coppock'].shift(2) > df['Coppock_Prev'])
    df.loc[buy_condition, 'Signal'] = 'Buy'
    
    # Alternative: Simple turn up from below zero
    turn_up_below_zero = (df['Coppock'] > df['Coppock_Prev']) & (df['Coppock'] < 0) & (df['Coppock_Prev'] < df['Coppock'].shift(2))
    df.loc[turn_up_below_zero, 'Signal'] = 'Potential Buy'
    
    # Zero line cross
    zero_cross_up = (df['Coppock'] > 0) & (df['Coppock_Prev'] <= 0)
    df.loc[zero_cross_up, 'Signal'] = 'Bullish Cross'
    
    zero_cross_down = (df['Coppock'] < 0) & (df['Coppock_Prev'] >= 0)
    df.loc[zero_cross_down, 'Signal'] = 'Bearish Cross'
    
    return df


class CoppockCurveGUI:
    """GUI for Coppock Curve Indicator."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("📈 Coppock Curve - Nifty 50")
        self.root.geometry("1400x900")
        
        # Database connection
        self.engine = get_engine()
        
        # Data storage
        self.data = None
        
        self._setup_ui()
        
        # Auto-load Nifty 50
        self.root.after(100, self._load_data)
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top control panel
        control_frame = ttk.LabelFrame(main_frame, text="Settings", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Symbol selection
        ttk.Label(control_frame, text="Index:").pack(side=tk.LEFT, padx=5)
        self.symbol_var = tk.StringVar(value="^NSEI")
        symbol_combo = ttk.Combobox(
            control_frame, 
            textvariable=self.symbol_var,
            values=["^NSEI", "^NSEBANK", "^BSESN"],
            width=12,
            state='readonly'
        )
        symbol_combo.pack(side=tk.LEFT, padx=5)
        
        # Timeframe
        ttk.Label(control_frame, text="Timeframe:").pack(side=tk.LEFT, padx=(20, 5))
        self.timeframe_var = tk.StringVar(value="Monthly")
        timeframe_combo = ttk.Combobox(
            control_frame,
            textvariable=self.timeframe_var,
            values=["Monthly", "Weekly"],
            width=10,
            state='readonly'
        )
        timeframe_combo.pack(side=tk.LEFT, padx=5)
        
        # Parameters
        ttk.Label(control_frame, text="ROC1:").pack(side=tk.LEFT, padx=(20, 5))
        self.roc1_var = tk.StringVar(value="14")
        roc1_spin = ttk.Spinbox(control_frame, textvariable=self.roc1_var, from_=5, to=20, width=5)
        roc1_spin.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(control_frame, text="ROC2:").pack(side=tk.LEFT, padx=(10, 5))
        self.roc2_var = tk.StringVar(value="11")
        roc2_spin = ttk.Spinbox(control_frame, textvariable=self.roc2_var, from_=5, to=20, width=5)
        roc2_spin.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(control_frame, text="WMA:").pack(side=tk.LEFT, padx=(10, 5))
        self.wma_var = tk.StringVar(value="10")
        wma_spin = ttk.Spinbox(control_frame, textvariable=self.wma_var, from_=5, to=20, width=5)
        wma_spin.pack(side=tk.LEFT, padx=2)
        
        # Lookback years
        ttk.Label(control_frame, text="Years:").pack(side=tk.LEFT, padx=(20, 5))
        self.years_var = tk.StringVar(value="10")
        years_combo = ttk.Combobox(
            control_frame,
            textvariable=self.years_var,
            values=["3", "5", "10", "15", "20", "All"],
            width=6,
            state='readonly'
        )
        years_combo.pack(side=tk.LEFT, padx=5)
        
        # Load button
        ttk.Button(control_frame, text="🔄 Calculate", command=self._load_data).pack(side=tk.LEFT, padx=20)
        
        # Status
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(control_frame, textvariable=self.status_var, style='Status.TLabel').pack(side=tk.RIGHT, padx=10)
        
        # Create style for status
        style = ttk.Style()
        style.configure('Status.TLabel', foreground='blue')
        
        # Split into chart and info panels
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left: Chart
        chart_frame = ttk.Frame(paned)
        paned.add(chart_frame, weight=3)
        
        self.fig = Figure(figsize=(12, 8), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Toolbar
        toolbar_frame = ttk.Frame(chart_frame)
        toolbar_frame.pack(fill=tk.X)
        NavigationToolbar2Tk(self.canvas, toolbar_frame)
        
        # Right: Info panel
        info_frame = ttk.Frame(paned)
        paned.add(info_frame, weight=1)
        
        # Current status
        status_frame = ttk.LabelFrame(info_frame, text="Current Status", padding=10)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.current_info = tk.Text(status_frame, height=8, width=35, font=('Consolas', 11))
        self.current_info.pack(fill=tk.X)
        self.current_info.config(state=tk.DISABLED)
        
        # Signals table
        signals_frame = ttk.LabelFrame(info_frame, text="Historical Signals", padding=5)
        signals_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('date', 'close', 'coppock', 'signal')
        self.signals_tree = ttk.Treeview(signals_frame, columns=columns, show='headings', height=20)
        
        headings = {
            'date': ('Date', 90),
            'close': ('Close', 80),
            'coppock': ('Coppock', 80),
            'signal': ('Signal', 100)
        }
        
        for col, (text, width) in headings.items():
            self.signals_tree.heading(col, text=text)
            self.signals_tree.column(col, width=width, anchor=tk.CENTER if col != 'signal' else tk.W)
        
        scrollbar = ttk.Scrollbar(signals_frame, orient=tk.VERTICAL, command=self.signals_tree.yview)
        self.signals_tree.configure(yscrollcommand=scrollbar.set)
        
        self.signals_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Color tags
        self.signals_tree.tag_configure('buy', background='#C8E6C9')
        self.signals_tree.tag_configure('potential_buy', background='#DCEDC8')
        self.signals_tree.tag_configure('bullish', background='#B3E5FC')
        self.signals_tree.tag_configure('bearish', background='#FFCDD2')
    
    def _load_data(self):
        """Load index data and calculate Coppock Curve."""
        symbol = self.symbol_var.get()
        timeframe = self.timeframe_var.get().lower()
        roc1 = int(self.roc1_var.get())
        roc2 = int(self.roc2_var.get())
        wma = int(self.wma_var.get())
        years = self.years_var.get()
        
        self.status_var.set("Loading data from Yahoo Finance...")
        
        def load():
            try:
                if not HAS_YFINANCE:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error", "yfinance not installed. Run: pip install yfinance"))
                    return
                
                # Calculate period
                if years == "All":
                    period = "max"
                else:
                    period = f"{years}y"
                
                # Download from Yahoo Finance
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=period, interval="1d")
                
                if df.empty:
                    self.root.after(0, lambda: self.status_var.set(f"No data found for {symbol}"))
                    return
                
                # Rename columns to lowercase
                df.columns = [c.lower() for c in df.columns]
                df.reset_index(inplace=True)
                df.rename(columns={'Date': 'date'}, inplace=True)
                
                # Ensure date is datetime
                df['date'] = pd.to_datetime(df['date'])
                if df['date'].dt.tz is not None:
                    df['date'] = df['date'].dt.tz_localize(None)
                
                df.set_index('date', inplace=True)
                
                # Resample to monthly or weekly
                if timeframe == 'monthly':
                    df_resampled = df.resample('ME').agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    }).dropna()
                else:  # weekly
                    df_resampled = df.resample('W-FRI').agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    }).dropna()
                
                df_resampled.reset_index(inplace=True)
                
                # Need enough data for Coppock calculation
                min_required = max(roc1, roc2) + wma
                if len(df_resampled) < min_required:
                    self.root.after(0, lambda: self.status_var.set(
                        f"Need {min_required} {timeframe} bars, only have {len(df_resampled)}"))
                    return
                
                # Calculate Coppock Curve
                result = calculate_coppock_curve(df_resampled, roc1, roc2, wma)
                
                self.data = result
                self.root.after(0, lambda: self._display_results(result, symbol, timeframe))
                
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
                import traceback
                traceback.print_exc()
        
        threading.Thread(target=load, daemon=True).start()
    
    def _display_results(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """Display the Coppock Curve results."""
        self.status_var.set(f"Loaded {len(df)} {timeframe} bars")
        
        # Update current info
        self._update_current_info(df, symbol, timeframe)
        
        # Update signals table
        self._update_signals_table(df)
        
        # Draw chart
        self._draw_chart(df, symbol, timeframe)
    
    def _update_current_info(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """Update the current status info panel."""
        self.current_info.config(state=tk.NORMAL)
        self.current_info.delete(1.0, tk.END)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # Determine trend
        if latest['Coppock'] > prev['Coppock']:
            trend = "↑ Rising"
            trend_color = "green"
        else:
            trend = "↓ Falling"
            trend_color = "red"
        
        # Determine zone
        if latest['Coppock'] > 0:
            zone = "Bullish Zone (Above Zero)"
        else:
            zone = "Bearish Zone (Below Zero)"
        
        # Determine signal
        signal = latest['Signal']
        if signal == 'None':
            if latest['Coppock'] < 0 and latest['Coppock'] > prev['Coppock']:
                signal = "⚠️ Watch for Buy Signal"
            elif latest['Coppock'] > 0:
                signal = "✅ Bullish Momentum"
            else:
                signal = "⏳ Waiting"
        
        symbol_name = {
            "^NSEI": "NIFTY 50",
            "^NSEBANK": "BANK NIFTY",
            "^BSESN": "SENSEX"
        }.get(symbol, symbol)
        
        text = f"""
{symbol_name} ({timeframe.title()})
{'=' * 30}

Date:     {latest['date'].strftime('%Y-%m-%d')}
Close:    {latest['close']:,.2f}

Coppock:  {latest['Coppock']:.2f}
Previous: {prev['Coppock']:.2f}
Change:   {latest['Coppock'] - prev['Coppock']:+.2f}

Trend:    {trend}
Zone:     {zone}

Signal:   {signal}
"""
        
        self.current_info.insert(1.0, text)
        self.current_info.config(state=tk.DISABLED)
    
    def _update_signals_table(self, df: pd.DataFrame):
        """Update the signals table."""
        for item in self.signals_tree.get_children():
            self.signals_tree.delete(item)
        
        # Filter rows with signals
        signals_df = df[df['Signal'] != 'None'].copy()
        
        # Also add recent rows for context
        recent = df.tail(10)
        
        # Combine and sort
        display_df = pd.concat([signals_df, recent]).drop_duplicates().sort_values('date', ascending=False)
        
        for _, row in display_df.iterrows():
            date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
            values = (
                date_str,
                f"{row['close']:,.0f}",
                f"{row['Coppock']:.2f}" if pd.notna(row['Coppock']) else "N/A",
                row['Signal']
            )
            
            # Determine tag
            signal = row['Signal']
            if signal == 'Buy':
                tag = 'buy'
            elif signal == 'Potential Buy':
                tag = 'potential_buy'
            elif signal == 'Bullish Cross':
                tag = 'bullish'
            elif signal == 'Bearish Cross':
                tag = 'bearish'
            else:
                tag = ''
            
            self.signals_tree.insert('', tk.END, values=values, tags=(tag,))
    
    def _draw_chart(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """Draw the Coppock Curve chart."""
        self.fig.clear()
        
        # Remove NaN values for plotting
        plot_df = df.dropna(subset=['Coppock'])
        
        if plot_df.empty:
            return
        
        # Create subplots: Price and Coppock
        ax1 = self.fig.add_subplot(211)
        ax2 = self.fig.add_subplot(212, sharex=ax1)
        
        # 1. Price chart
        ax1.plot(plot_df['date'], plot_df['close'], 'k-', linewidth=1.5, label='Close')
        ax1.fill_between(plot_df['date'], plot_df['close'], alpha=0.1)
        
        # Mark buy signals on price
        buy_signals = plot_df[plot_df['Signal'].isin(['Buy', 'Potential Buy'])]
        if not buy_signals.empty:
            ax1.scatter(buy_signals['date'], buy_signals['close'], 
                       c='green', s=100, marker='^', zorder=5, 
                       label='Buy Signal', edgecolors='darkgreen', linewidth=1)
        
        # Mark bullish/bearish crosses
        bullish_cross = plot_df[plot_df['Signal'] == 'Bullish Cross']
        if not bullish_cross.empty:
            ax1.scatter(bullish_cross['date'], bullish_cross['close'],
                       c='blue', s=80, marker='o', zorder=5,
                       label='Bullish Cross', edgecolors='darkblue', linewidth=1)
        
        bearish_cross = plot_df[plot_df['Signal'] == 'Bearish Cross']
        if not bearish_cross.empty:
            ax1.scatter(bearish_cross['date'], bearish_cross['close'],
                       c='red', s=80, marker='o', zorder=5,
                       label='Bearish Cross', edgecolors='darkred', linewidth=1)
        
        symbol_name = {
            "^NSEI": "NIFTY 50",
            "^NSEBANK": "BANK NIFTY",
            "^BSESN": "SENSEX"
        }.get(symbol, symbol)
        
        ax1.set_title(f'{symbol_name} - {timeframe.title()} Close Price', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Price')
        ax1.legend(loc='upper left', fontsize=9)
        ax1.grid(True, alpha=0.3)
        
        # 2. Coppock Curve
        # Color based on positive/negative
        colors = ['#4CAF50' if c >= 0 else '#F44336' for c in plot_df['Coppock']]
        
        # Plot as bars for better visibility
        ax2.bar(plot_df['date'], plot_df['Coppock'], color=colors, alpha=0.7, width=20 if timeframe == 'monthly' else 5)
        
        # Also plot as line for trend visibility
        ax2.plot(plot_df['date'], plot_df['Coppock'], 'k-', linewidth=1, alpha=0.5)
        
        # Zero line
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=1.5)
        
        # Mark signals on Coppock
        if not buy_signals.empty:
            ax2.scatter(buy_signals['date'], buy_signals['Coppock'],
                       c='green', s=100, marker='^', zorder=5,
                       edgecolors='darkgreen', linewidth=1)
        
        # Highlight current value
        latest = plot_df.iloc[-1]
        ax2.annotate(f'{latest["Coppock"]:.2f}',
                    xy=(latest['date'], latest['Coppock']),
                    xytext=(10, 10), textcoords='offset points',
                    fontsize=10, fontweight='bold',
                    color='green' if latest['Coppock'] >= 0 else 'red',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
        
        roc1 = self.roc1_var.get()
        roc2 = self.roc2_var.get()
        wma = self.wma_var.get()
        ax2.set_title(f'Coppock Curve ({roc1}, {roc2}, {wma})', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Coppock Value')
        ax2.set_xlabel('Date')
        ax2.grid(True, alpha=0.3)
        
        # Format x-axis
        if timeframe == 'monthly':
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax2.xaxis.set_major_locator(mdates.YearLocator())
        else:
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        self.fig.autofmt_xdate()
        self.fig.tight_layout()
        self.canvas.draw()


def main():
    """Main entry point."""
    root = tk.Tk()
    app = CoppockCurveGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
