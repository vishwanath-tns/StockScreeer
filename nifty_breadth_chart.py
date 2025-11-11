#!/usr/bin/env python3
"""
Nifty with Market Breadth Chart Display
Shows Nifty index chart on top and bullish/bearish stock counts below
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.market_breadth_service import get_nifty_with_breadth_chart_data


class NiftyBreadthChartWindow:
    """Window to display Nifty chart with market breadth indicators."""
    
    def __init__(self, parent, start_date, end_date, index_name='NIFTY 50'):
        self.parent = parent
        self.start_date = start_date
        self.end_date = end_date
        self.index_name = index_name
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title(f"{index_name} with Market Breadth - {start_date} to {end_date}")
        self.window.geometry("1200x800")
        self.window.transient(parent)
        
        # Add maximize button and resizable window
        self.window.resizable(True, True)
        self.window.state('normal')  # Can be maximized by user
        
        # Add window icon if available
        try:
            self.window.iconbitmap(default='')  # Use default icon
        except:
            pass  # Ignore if no icon available
        
        # Create main frame
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(title_frame, text=f"{index_name} with Market Breadth Analysis", 
                 font=('Arial', 16, 'bold')).pack(side=tk.LEFT)
        
        ttk.Label(title_frame, text=f"{start_date} to {end_date}", 
                 font=('Arial', 12), foreground='blue').pack(side=tk.LEFT, padx=(20, 0))
        
        # Add window control buttons
        controls_frame = ttk.Frame(title_frame)
        controls_frame.pack(side=tk.RIGHT)
        
        # Maximize/Restore button
        self.is_maximized = False
        self.normal_geometry = "1200x800"
        self.maximize_btn = ttk.Button(controls_frame, text="⬜ Maximize", 
                                     command=self.toggle_maximize)
        self.maximize_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Refresh button
        ttk.Button(controls_frame, text="🔄 Refresh", 
                  command=self.refresh_chart).pack(side=tk.RIGHT, padx=(0, 5))
        
        # Create chart frame
        self.chart_frame = ttk.Frame(main_frame)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Loading chart data...", foreground="orange")
        self.status_label.pack(pady=(5, 0))
        
        # Load and display data
        self.load_chart_data()
    
    def toggle_maximize(self):
        """Toggle between maximized and normal window state."""
        if self.is_maximized:
            # Restore to normal size
            self.window.state('normal')
            self.window.geometry(self.normal_geometry)
            self.maximize_btn.config(text="⬜ Maximize")
            self.is_maximized = False
        else:
            # Store current geometry
            self.normal_geometry = self.window.geometry()
            # Maximize window
            self.window.state('zoomed')  # Windows maximize
            self.maximize_btn.config(text="🗗 Restore")
            self.is_maximized = True
    
    def refresh_chart(self):
        """Refresh the chart data and display."""
        self.status_label.config(text="Refreshing chart data...", foreground="orange")
        
        # Clear existing chart
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # Reload data
        self.load_chart_data()
    
    def load_chart_data(self):
        """Load and display the chart data."""
        try:
            # Get data from service
            data = get_nifty_with_breadth_chart_data(self.start_date, self.end_date, self.index_name)
            
            if not data.get('success'):
                error_msg = data.get('error', 'Unknown error')
                self.status_label.config(text=f"❌ Error: {error_msg}", foreground="red")
                messagebox.showerror("Data Error", f"Failed to load chart data:\n{error_msg}")
                return
            
            # Create the chart
            self.create_chart(data)
            
            total_days = data.get('total_days', 0)
            self.status_label.config(text=f"✅ Loaded {total_days} trading days", foreground="green")
            
        except Exception as e:
            error_msg = f"Failed to load chart: {str(e)}"
            self.status_label.config(text=f"❌ {error_msg}", foreground="red")
            messagebox.showerror("Chart Error", error_msg)
            print(f"Chart error: {e}")
            import traceback
            traceback.print_exc()
    
    def create_chart(self, data):
        """Create the dual-panel chart."""
        nifty_data = data['nifty_data']
        breadth_data = data['breadth_data']
        combined_data = data['combined_data']
        
        if combined_data.empty:
            self.status_label.config(text="❌ No data to display", foreground="red")
            return
        
        # Check for data synchronization issues
        nifty_available = not combined_data['close'].isna().all()
        breadth_available = not combined_data['bullish_count'].isna().all()
        
        if nifty_available and breadth_available:
            # Check overlap
            nifty_dates = set(combined_data[combined_data['close'].notna()]['trade_date'])
            breadth_dates = set(combined_data[combined_data['bullish_count'].notna()]['trade_date'])
            overlap = len(nifty_dates.intersection(breadth_dates))
            total_dates = len(nifty_dates.union(breadth_dates))
            
            if overlap / total_dates < 0.5:  # Less than 50% overlap
                print(f"⚠️ Warning: Limited data synchronization - {overlap}/{total_dates} dates overlap")
        elif not nifty_available:
            print(f"⚠️ Warning: No Nifty data available for the selected period")
        elif not breadth_available:
            print(f"⚠️ Warning: No market breadth data available for the selected period")
        
        # Create figure with subplots
        fig = Figure(figsize=(14, 10), dpi=100)
        
        # Create two subplots: Nifty on top (larger), breadth below
        ax1 = fig.add_subplot(2, 1, 1)  # Nifty chart (60% height)
        ax2 = fig.add_subplot(2, 1, 2)  # Breadth chart (40% height)
        
        # Adjust subplot spacing
        fig.subplots_adjust(hspace=0.3, left=0.08, right=0.95, top=0.95, bottom=0.15)
        
        # Ensure trade_date is datetime
        combined_data['trade_date'] = pd.to_datetime(combined_data['trade_date'])
        
        # Create separate datasets for plotting to handle missing data properly
        nifty_plot_data = combined_data[combined_data['close'].notna()].copy()
        breadth_plot_data = combined_data[combined_data['bullish_count'].notna()].copy()
        
        # Plot 1: Nifty Index Chart
        if not nifty_plot_data.empty and 'close' in nifty_plot_data.columns:
            nifty_dates = nifty_plot_data['trade_date']
            nifty_closes = nifty_plot_data['close']
            
            ax1.plot(nifty_dates, nifty_closes, color='#1f77b4', linewidth=2, label=f'{self.index_name}')
            ax1.fill_between(nifty_dates, nifty_closes, alpha=0.3, color='#1f77b4')
            
            # Add moving average if enough data
            if len(nifty_closes) >= 20:
                ma20 = nifty_closes.rolling(window=20, min_periods=1).mean()
                ax1.plot(nifty_dates, ma20, color='red', linewidth=1, alpha=0.7, label='20-day MA')
            
            # Set Y-axis limits to actual price range with small padding
            price_min = nifty_closes.min()
            price_max = nifty_closes.max()
            price_range = price_max - price_min
            padding = price_range * 0.05  # 5% padding
            ax1.set_ylim(price_min - padding, price_max + padding)
            
            # Format Y-axis to show price values with commas
            ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
            
            ax1.set_title(f'{self.index_name} Price Chart', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Price Level', fontsize=12)
            ax1.legend(loc='upper left')
            ax1.grid(True, alpha=0.3)
            
            # Format x-axis with better date formatting
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
            if len(nifty_dates) > 20:
                ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            else:
                ax1.xaxis.set_major_locator(mdates.DayLocator(interval=2))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # Set x-axis limits to match the data range
            ax1.set_xlim(nifty_dates.min(), nifty_dates.max())
        else:
            ax1.text(0.5, 0.5, f'No {self.index_name} data available', 
                    transform=ax1.transAxes, ha='center', va='center', fontsize=12)
            ax1.set_title(f'{self.index_name} Price Chart (No Data)', fontsize=14)
        
        # Plot 2: Market Breadth Chart
        if not breadth_plot_data.empty and 'bullish_count' in breadth_plot_data.columns:
            breadth_dates = breadth_plot_data['trade_date']
            bullish_counts = breadth_plot_data['bullish_count']
            bearish_counts = breadth_plot_data['bearish_count']
            
            # Plot bullish and bearish counts
            ax2.plot(breadth_dates, bullish_counts, color='green', linewidth=2, 
                    marker='o', markersize=4, label='Bullish Stocks')
            ax2.plot(breadth_dates, bearish_counts, color='red', linewidth=2, 
                    marker='s', markersize=4, label='Bearish Stocks')
            
            # Fill areas
            ax2.fill_between(breadth_dates, bullish_counts, alpha=0.3, color='green')
            ax2.fill_between(breadth_dates, bearish_counts, alpha=0.3, color='red')
            
            # Add neutral line if available
            if 'neutral_count' in breadth_plot_data.columns:
                neutral_counts = breadth_plot_data['neutral_count']
                ax2.plot(breadth_dates, neutral_counts, color='gray', linewidth=1, 
                        alpha=0.7, label='Neutral Stocks')
            
            ax2.set_title('Market Breadth - Bullish vs Bearish Stock Counts', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Number of Stocks', fontsize=12)
            ax2.set_xlabel('Date', fontsize=12)
            ax2.legend(loc='upper left')
            ax2.grid(True, alpha=0.3)
            
            # Format x-axis with better date formatting - sync with top chart
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
            if len(breadth_dates) > 20:
                ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            else:
                ax2.xaxis.set_major_locator(mdates.DayLocator(interval=2))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # Synchronize x-axis limits with top chart if both have data
            if not nifty_plot_data.empty:
                # Use the common date range for both charts
                common_start = max(nifty_plot_data['trade_date'].min(), breadth_dates.min())
                common_end = min(nifty_plot_data['trade_date'].max(), breadth_dates.max())
                ax1.set_xlim(common_start, common_end)
                ax2.set_xlim(common_start, common_end)
            else:
                ax2.set_xlim(breadth_dates.min(), breadth_dates.max())
            
            # Format Y-axis to show stock counts with commas
            ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
            
            # Add some statistics as text
            avg_bullish = bullish_counts.mean()
            avg_bearish = bearish_counts.mean()
            total_avg = avg_bullish + avg_bearish
            bullish_pct = (avg_bullish / total_avg * 100) if total_avg > 0 else 0
            
            # Add data availability info to stats
            nifty_days = len(nifty_plot_data) if not nifty_plot_data.empty else 0
            breadth_days = len(breadth_plot_data)
            
            stats_text = f'Period Averages:\nBullish: {avg_bullish:.0f} ({bullish_pct:.1f}%)\nBearish: {avg_bearish:.0f} ({100-bullish_pct:.1f}%)\n\nData Points:\nNifty: {nifty_days} days\nBreadth: {breadth_days} days'
            ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes, 
                    verticalalignment='top', fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.8))
            
        else:
            ax2.text(0.5, 0.5, 'No market breadth data available', 
                    transform=ax2.transAxes, ha='center', va='center', fontsize=12)
            ax2.set_title('Market Breadth (No Data)', fontsize=14)
        
        # Add to tkinter window
        canvas = FigureCanvasTkAgg(fig, self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add toolbar for zooming/panning
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar = NavigationToolbar2Tk(canvas, self.chart_frame)
        toolbar.update()


def show_nifty_breadth_chart(parent, start_date, end_date, index_name='NIFTY 50'):
    """
    Show Nifty with market breadth chart window.
    
    Args:
        parent: Parent tkinter window
        start_date: Start date for chart
        end_date: End date for chart  
        index_name: Index name (default: 'NIFTY 50')
    """
    return NiftyBreadthChartWindow(parent, start_date, end_date, index_name)


# Test function
def test_nifty_breadth_chart():
    """Test the Nifty breadth chart display."""
    root = tk.Tk()
    root.title("Nifty Breadth Chart Test")
    root.geometry("400x200")
    
    def show_test_chart():
        from datetime import datetime, timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        show_nifty_breadth_chart(root, start_date, end_date)
    
    ttk.Button(root, text="Show Test Chart (Last 30 Days)", 
              command=show_test_chart).pack(expand=True)
    
    root.mainloop()


if __name__ == "__main__":
    test_nifty_breadth_chart()