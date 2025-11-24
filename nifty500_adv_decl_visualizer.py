"""
Nifty 500 Advance-Decline Visualizer
====================================

Interactive chart showing Nifty 50 index with advance-decline indicator below.

Features:
- Dual-panel chart (Nifty candles + A/D indicator)
- Date range selector
- No weekend gaps (business days only)
- Default 6 months view
- Interactive zoom and pan
- Professional styling
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import Optional, Tuple
import pandas as pd
import numpy as np
from sqlalchemy import text
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import mplfinance as mpf
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import logging

# Import calculator module
from nifty500_adv_decl_calculator import (
    get_db_engine,
    get_advance_decline_data,
    compute_date_range
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Nifty500AdvDeclVisualizer:
    """
    Interactive visualizer for Nifty 500 advance-decline analysis
    """
    
    def __init__(self, master):
        self.master = master
        self.master.title("Nifty 500 Advance-Decline Analyzer")
        self.master.geometry("1400x900")
        
        # Data
        self.nifty_data = None
        self.adv_decl_data = None
        self.engine = get_db_engine()
        
        # Default date range (6 months)
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=180)
        
        # Setup UI
        self.setup_ui()
        
        # Load initial data
        self.load_and_plot()
    
    def setup_ui(self):
        """Setup user interface"""
        
        # Control Frame
        control_frame = ttk.Frame(self.master, padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Title
        title_label = ttk.Label(
            control_frame,
            text="📊 Nifty 500 Advance-Decline Analysis",
            font=('Helvetica', 14, 'bold')
        )
        title_label.pack(side=tk.LEFT, padx=5)
        
        # Date range selectors
        ttk.Label(control_frame, text="From:").pack(side=tk.LEFT, padx=5)
        self.start_date_entry = DateEntry(
            control_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd'
        )
        self.start_date_entry.set_date(self.start_date)
        self.start_date_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="To:").pack(side=tk.LEFT, padx=5)
        self.end_date_entry = DateEntry(
            control_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd'
        )
        self.end_date_entry.set_date(self.end_date)
        self.end_date_entry.pack(side=tk.LEFT, padx=5)
        
        # Update button
        self.update_btn = ttk.Button(
            control_frame,
            text="Update Chart",
            command=self.update_chart
        )
        self.update_btn.pack(side=tk.LEFT, padx=10)
        
        # Quick range buttons
        ttk.Button(
            control_frame,
            text="1M",
            command=lambda: self.set_quick_range(30)
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            control_frame,
            text="3M",
            command=lambda: self.set_quick_range(90)
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            control_frame,
            text="6M",
            command=lambda: self.set_quick_range(180)
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            control_frame,
            text="1Y",
            command=lambda: self.set_quick_range(365)
        ).pack(side=tk.LEFT, padx=2)
        
        # Compute button
        ttk.Button(
            control_frame,
            text="⚙️ Compute A/D",
            command=self.compute_advance_decline
        ).pack(side=tk.LEFT, padx=20)
        
        # Status label
        self.status_label = ttk.Label(
            control_frame,
            text="Ready",
            foreground="green"
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # Chart Frame
        self.chart_frame = ttk.Frame(self.master)
        self.chart_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Info Frame
        info_frame = ttk.Frame(self.master, padding="10")
        info_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.info_label = ttk.Label(
            info_frame,
            text="",
            font=('Helvetica', 10)
        )
        self.info_label.pack(side=tk.LEFT)
    
    def set_quick_range(self, days: int):
        """Set quick date range"""
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=days)
        self.start_date_entry.set_date(self.start_date)
        self.end_date_entry.set_date(self.end_date)
        self.update_chart()
    
    def load_nifty_data(self, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Load Nifty 50 data from yfinance_daily_quotes
        
        Returns:
            DataFrame with OHLCV data
        """
        query = text("""
            SELECT 
                date,
                open,
                high,
                low,
                close,
                volume
            FROM yfinance_daily_quotes
            WHERE symbol = 'NIFTY'
                AND date BETWEEN :start_date AND :end_date
            ORDER BY date
        """)
        
        df = pd.read_sql(
            query,
            self.engine,
            params={'start_date': start_date, 'end_date': end_date},
            parse_dates=['date']
        )
        
        if not df.empty:
            df.set_index('date', inplace=True)
        
        return df
    
    def load_advance_decline_data(self, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Load advance/decline data
        
        Returns:
            DataFrame with A/D counts
        """
        df = get_advance_decline_data(start_date, end_date)
        
        if not df.empty:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.set_index('trade_date', inplace=True)
            df.sort_index(inplace=True)
        
        return df
    
    def load_and_plot(self):
        """Load data and create plot"""
        self.status_label.config(text="Loading data...", foreground="orange")
        self.master.update()
        
        try:
            # Get date range
            start_date = self.start_date_entry.get_date()
            end_date = self.end_date_entry.get_date()
            
            # Load data
            self.nifty_data = self.load_nifty_data(start_date, end_date)
            self.adv_decl_data = self.load_advance_decline_data(start_date, end_date)
            
            if self.nifty_data.empty:
                messagebox.showwarning(
                    "No Data",
                    "No Nifty 50 data found for the selected date range."
                )
                self.status_label.config(text="No data", foreground="red")
                return
            
            if self.adv_decl_data.empty:
                messagebox.showwarning(
                    "No A/D Data",
                    "No advance/decline data found. Click 'Compute A/D' to calculate."
                )
                self.status_label.config(text="No A/D data", foreground="red")
                # Still plot Nifty data
            
            # Create plot
            self.create_plot()
            
            # Update info
            nifty_days = len(self.nifty_data)
            ad_days = len(self.adv_decl_data) if not self.adv_decl_data.empty else 0
            self.info_label.config(
                text=f"📅 Period: {start_date} to {end_date} | "
                     f"Nifty: {nifty_days} days | A/D: {ad_days} days"
            )
            
            self.status_label.config(text="Ready", foreground="green")
            
        except Exception as e:
            logger.error(f"Error loading data: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to load data: {e}")
            self.status_label.config(text="Error", foreground="red")
    
    def create_plot(self):
        """Create dual-panel chart"""
        
        # Clear existing chart
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # Create figure with subplots
        fig = Figure(figsize=(14, 9), facecolor='white')
        
        # Subplot 1: Nifty candlestick chart (70% height)
        ax1 = fig.add_subplot(2, 1, 1)
        
        # Subplot 2: Advance-Decline indicator (30% height)
        ax2 = fig.add_subplot(2, 1, 2, sharex=ax1)
        
        fig.subplots_adjust(hspace=0.05)
        
        # Plot Nifty candlesticks
        self.plot_nifty_candlesticks(ax1)
        
        # Plot advance-decline indicator
        if not self.adv_decl_data.empty:
            self.plot_advance_decline(ax2)
        else:
            ax2.text(
                0.5, 0.5,
                'No Advance-Decline Data\nClick "Compute A/D" to calculate',
                ha='center', va='center',
                transform=ax2.transAxes,
                fontsize=12,
                color='gray'
            )
            if hasattr(self, 'positions'):
                ax2.set_xlim(-0.5, len(self.positions) - 0.5)
        
        # Format x-axis (business days only)
        self.format_business_days_axis(ax2)
        
        # Create canvas
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Add toolbar
        toolbar = NavigationToolbar2Tk(canvas, self.chart_frame)
        toolbar.update()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    
    def plot_nifty_candlesticks(self, ax):
        """Plot Nifty candlestick chart (no weekend gaps)"""
        
        df = self.nifty_data.copy()
        
        # Use integer positions (0, 1, 2, ...) to avoid weekend gaps
        positions = np.arange(len(df))
        
        # Plot candlesticks manually using integer positions
        width = 0.6
        
        for i, (idx, row) in enumerate(df.iterrows()):
            pos = positions[i]
            
            # Candle body
            height = row['close'] - row['open']
            bottom = min(row['open'], row['close'])
            color = 'green' if row['close'] >= row['open'] else 'red'
            alpha = 0.8
            
            rect = Rectangle(
                (pos - width/2, bottom),
                width, abs(height),
                facecolor=color, edgecolor=color, alpha=alpha
            )
            ax.add_patch(rect)
            
            # High wick
            ax.plot(
                [pos, pos],
                [max(row['open'], row['close']), row['high']],
                color=color, linewidth=1, alpha=0.8
            )
            
            # Low wick
            ax.plot(
                [pos, pos],
                [min(row['open'], row['close']), row['low']],
                color=color, linewidth=1, alpha=0.8
            )
        
        # Store positions and dates for x-axis formatting
        self.positions = positions
        self.dates = df.index
        
        # Calculate price change
        start_price = df['close'].iloc[0]
        end_price = df['close'].iloc[-1]
        pct_change = ((end_price - start_price) / start_price) * 100
        
        # Set labels and title
        ax.set_ylabel('Nifty 50 Price', fontsize=11, fontweight='bold')
        title = f'Nifty 50 Index'
        subtitle = f'  ({start_price:.2f} → {end_price:.2f}, {pct_change:+.2f}%)'
        ax.set_title(title + subtitle, fontsize=13, fontweight='bold', pad=10)
        
        # Style
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlim(-0.5, len(df) - 0.5)
        
        # Remove x-axis labels (shared with bottom plot)
        ax.set_xticklabels([])
        
        # Set integer x-axis positions
        ax.set_xticks(positions[::max(1, len(positions)//10)])  # Show ~10 ticks
    
    def plot_advance_decline(self, ax):
        """Plot advance-decline indicator as separate lines (no weekend gaps)"""
        
        df = self.adv_decl_data.copy()
        
        # Use same integer positions as candlesticks
        positions = np.arange(len(df))
        
        # Plot advances as green line
        ax.plot(
            positions,
            df['advances'],
            color='green',
            linewidth=2,
            alpha=0.8,
            label='Advances',
            marker='o',
            markersize=3
        )
        
        # Plot declines as red line
        ax.plot(
            positions,
            df['declines'],
            color='red',
            linewidth=2,
            alpha=0.8,
            label='Declines',
            marker='o',
            markersize=3
        )
        
        # Plot unchanged as gray line (optional, usually small)
        if 'unchanged' in df.columns:
            ax.plot(
                positions,
                df['unchanged'],
                color='gray',
                linewidth=1.5,
                alpha=0.5,
                label='Unchanged',
                linestyle='--'
            )
        
        # Fill area between advances and declines
        ax.fill_between(
            positions,
            df['advances'],
            df['declines'],
            where=(df['advances'] >= df['declines']),
            color='green',
            alpha=0.2,
            interpolate=True
        )
        ax.fill_between(
            positions,
            df['advances'],
            df['declines'],
            where=(df['advances'] < df['declines']),
            color='red',
            alpha=0.2,
            interpolate=True
        )
        
        # Labels
        ax.set_ylabel('Number of Stocks', fontsize=11, fontweight='bold')
        ax.set_xlabel('Date', fontsize=11, fontweight='bold')
        
        # Title with statistics
        avg_advances = df['advances'].mean()
        avg_declines = df['declines'].mean()
        avg_advance_pct = df['advance_pct'].mean()
        
        title = f'Advance-Decline Lines  '
        subtitle = f'(Avg Advances: {avg_advances:.0f}, Avg Declines: {avg_declines:.0f}, {avg_advance_pct:.1f}%)'
        ax.set_title(title + subtitle, fontsize=11, fontweight='bold', pad=10)
        
        # Style
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Legend
        ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
        
        # Set x-axis limits to match positions
        ax.set_xlim(-0.5, len(df) - 0.5)
    
    def format_business_days_axis(self, ax):
        """Format x-axis to show business days only (no weekend gaps)"""
        
        # Use integer positions with date labels
        if hasattr(self, 'dates') and len(self.dates) > 0:
            # Select ~10 tick positions evenly distributed
            n_ticks = min(10, len(self.dates))
            tick_indices = np.linspace(0, len(self.dates) - 1, n_ticks, dtype=int)
            
            ax.set_xticks(tick_indices)
            ax.set_xticklabels(
                [self.dates[i].strftime('%b %d\n%Y') for i in tick_indices],
                rotation=45, ha='right'
            )
    
    def update_chart(self):
        """Update chart with new date range"""
        self.load_and_plot()
    
    def compute_advance_decline(self):
        """Compute advance-decline data for selected range"""
        
        start_date = self.start_date_entry.get_date()
        end_date = self.end_date_entry.get_date()
        
        # Confirm
        response = messagebox.askyesno(
            "Compute A/D Data",
            f"This will compute advance-decline data from {start_date} to {end_date}.\n\n"
            f"This may take a few minutes depending on the date range.\n\n"
            f"Continue?"
        )
        
        if not response:
            return
        
        # Create progress window
        progress_window = tk.Toplevel(self.master)
        progress_window.title("Computing...")
        progress_window.geometry("400x150")
        progress_window.transient(self.master)
        progress_window.grab_set()
        
        ttk.Label(
            progress_window,
            text="Computing Advance-Decline Data",
            font=('Helvetica', 12, 'bold')
        ).pack(pady=10)
        
        progress_label = ttk.Label(progress_window, text="Initializing...")
        progress_label.pack(pady=5)
        
        progress_bar = ttk.Progressbar(
            progress_window,
            mode='determinate',
            length=350
        )
        progress_bar.pack(pady=10)
        
        # Progress callback
        def update_progress(current, total, message):
            progress = (current / total) * 100
            progress_bar['value'] = progress
            progress_label.config(text=f"{message} ({current}/{total})")
            progress_window.update()
        
        try:
            # Compute
            stats = compute_date_range(
                start_date,
                end_date,
                force_update=False,
                progress_callback=update_progress
            )
            
            # Close progress window
            progress_window.destroy()
            
            # Show results
            messagebox.showinfo(
                "Computation Complete",
                f"Successfully computed advance-decline data!\n\n"
                f"Processed: {stats['processed']} days\n"
                f"New entries: {stats['new']}\n"
                f"Skipped: {stats['skipped']}\n"
                f"Failed: {stats['failed']}"
            )
            
            # Reload chart
            self.load_and_plot()
            
        except Exception as e:
            progress_window.destroy()
            logger.error(f"Error computing: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to compute: {e}")


def main():
    """Main function"""
    root = tk.Tk()
    app = Nifty500AdvDeclVisualizer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
