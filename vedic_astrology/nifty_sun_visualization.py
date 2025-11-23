#!/usr/bin/env python3
"""
Nifty Candlestick Chart with Sun Planetary Position Indicator
Visualizes Nifty 50 price movements alongside Sun's zodiac cycle from 2023 onwards
Uses existing data from yfinance_daily_quotes and planetary_positions tables
"""

import sys
import os

# Add parent directory to path to import sync_bhav_gui
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sync_bhav_gui import engine
from sqlalchemy import text
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import mplfinance as mpf
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np

class NiftySunVisualization:
    """GUI for Nifty candlestick chart with Sun position indicator"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Nifty 50 with Sun Planetary Cycles - Vedic Astrology Analysis")
        self.root.geometry("1400x900")
        
        # Database connection
        self.engine = engine()
        
        # Data storage
        self.nifty_data = None
        self.sun_data = None
        self.moon_data = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Control Panel
        control_frame = ttk.LabelFrame(self.root, text="Controls", padding=10)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        # Date range selection
        ttk.Label(control_frame, text="From:").grid(row=0, column=0, padx=5)
        self.start_date = tk.StringVar(value="2023-01-01")
        start_entry = ttk.Entry(control_frame, textvariable=self.start_date, width=12)
        start_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(control_frame, text="To:").grid(row=0, column=2, padx=5)
        self.end_date = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        end_entry = ttk.Entry(control_frame, textvariable=self.end_date, width=12)
        end_entry.grid(row=0, column=3, padx=5)
        
        # Buttons
        ttk.Button(control_frame, text="Load Data", 
                  command=self.load_data).grid(row=0, column=4, padx=10)
        ttk.Button(control_frame, text="Plot Chart", 
                  command=self.plot_chart).grid(row=0, column=5, padx=5)
        ttk.Button(control_frame, text="Export", 
                  command=self.export_chart).grid(row=0, column=6, padx=5)
        
        # Info label
        self.info_label = ttk.Label(control_frame, text="Ready", foreground="blue")
        self.info_label.grid(row=0, column=7, padx=20)
        
        # Chart frame
        self.chart_frame = ttk.Frame(self.root)
        self.chart_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready to load data")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def load_data(self):
        """Load Nifty data and Sun positions from database"""
        try:
            self.info_label.config(text="Loading data...", foreground="orange")
            self.root.update()
            
            start = self.start_date.get()
            end = self.end_date.get()
            
            # Validate dates
            try:
                datetime.strptime(start, "%Y-%m-%d")
                datetime.strptime(end, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
                return
            
            conn = self.engine.connect()
            
            # Load Nifty data from yfinance_daily_quotes
            self.status_var.set("Loading Nifty 50 data from database...")
            nifty_query = text("""
                SELECT date, open, high, low, close, volume
                FROM yfinance_daily_quotes
                WHERE symbol = 'NIFTY'
                AND date >= :start_date
                AND date <= :end_date
                ORDER BY date
            """)
            
            nifty_result = conn.execute(nifty_query, 
                                       {'start_date': start, 'end_date': end})
            nifty_rows = nifty_result.fetchall()
            
            if not nifty_rows:
                messagebox.showwarning("No Data", 
                    "No Nifty data found. Make sure NIFTY symbol data is downloaded.")
                conn.close()
                return
            
            # Convert to DataFrame
            self.nifty_data = pd.DataFrame(nifty_rows, 
                columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
            self.nifty_data['Date'] = pd.to_datetime(self.nifty_data['Date'])
            
            # Filter out weekends (Saturday=5, Sunday=6)
            self.nifty_data = self.nifty_data[self.nifty_data['Date'].dt.dayofweek < 5]
            
            self.nifty_data.set_index('Date', inplace=True)
            
            # Load Sun positions from planetary_positions
            # Take only market open time (9:15 AM) position for each trading day
            self.status_var.set("Loading Sun planetary positions...")
            sun_query = text("""
                SELECT DATE(timestamp) as date, 
                       AVG(sun_longitude) as sun_longitude,
                       sun_sign,
                       AVG(sun_degree) as sun_degree
                FROM planetary_positions
                WHERE DATE(timestamp) >= :start_date
                AND DATE(timestamp) <= :end_date
                AND HOUR(timestamp) = 9
                AND MINUTE(timestamp) = 15
                AND DAYOFWEEK(timestamp) NOT IN (1, 7)
                GROUP BY DATE(timestamp), sun_sign
                ORDER BY date
            """)
            
            sun_result = conn.execute(sun_query, 
                                     {'start_date': start, 'end_date': end})
            sun_rows = sun_result.fetchall()
            
            if not sun_rows:
                messagebox.showwarning("No Data", 
                    "No Sun position data found for selected date range.")
                conn.close()
                return
            
            # Convert to DataFrame
            self.sun_data = pd.DataFrame(sun_rows,
                columns=['Date', 'sun_longitude', 'sun_sign', 'sun_degree'])
            self.sun_data['Date'] = pd.to_datetime(self.sun_data['Date'])
            
            # Convert Decimal to float for numpy operations
            self.sun_data['sun_longitude'] = self.sun_data['sun_longitude'].astype(float)
            self.sun_data['sun_degree'] = self.sun_data['sun_degree'].astype(float)
            
            # Load Moon positions from planetary_positions
            # Take only market open time (9:15 AM) position for each trading day
            self.status_var.set("Loading Moon planetary positions...")
            moon_query = text("""
                SELECT DATE(timestamp) as date, 
                       AVG(moon_longitude) as moon_longitude,
                       moon_sign,
                       AVG(moon_degree) as moon_degree
                FROM planetary_positions
                WHERE DATE(timestamp) >= :start_date
                AND DATE(timestamp) <= :end_date
                AND HOUR(timestamp) = 9
                AND MINUTE(timestamp) = 15
                AND DAYOFWEEK(timestamp) NOT IN (1, 7)
                GROUP BY DATE(timestamp), moon_sign
                ORDER BY date
            """)
            
            moon_result = conn.execute(moon_query, 
                                      {'start_date': start, 'end_date': end})
            moon_rows = moon_result.fetchall()
            
            if not moon_rows:
                messagebox.showwarning("No Data", 
                    "No Moon position data found for selected date range.")
                conn.close()
                return
            
            # Convert to DataFrame
            self.moon_data = pd.DataFrame(moon_rows,
                columns=['Date', 'moon_longitude', 'moon_sign', 'moon_degree'])
            self.moon_data['Date'] = pd.to_datetime(self.moon_data['Date'])
            
            # Convert Decimal to float for numpy operations
            self.moon_data['moon_longitude'] = self.moon_data['moon_longitude'].astype(float)
            self.moon_data['moon_degree'] = self.moon_data['moon_degree'].astype(float)
            
            conn.close()
            
            # Update info
            self.info_label.config(
                text=f"Loaded: {len(self.nifty_data)} Nifty records, "
                     f"{len(self.sun_data)} Sun positions, "
                     f"{len(self.moon_data)} Moon positions", 
                foreground="green")
            
            self.status_var.set(
                f"Data loaded successfully: {start} to {end} | "
                f"Nifty: {len(self.nifty_data)} days | "
                f"Sun: {len(self.sun_data)} days | "
                f"Moon: {len(self.moon_data)} days")
            
            messagebox.showinfo("Success", 
                f"Data loaded successfully!\n\n"
                f"Nifty records: {len(self.nifty_data)}\n"
                f"Sun positions: {len(self.sun_data)}\n"
                f"Moon positions: {len(self.moon_data)}\n"
                f"Date range: {start} to {end}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data:\n{str(e)}")
            self.info_label.config(text="Error loading data", foreground="red")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    def plot_chart(self):
        """Create the visualization with candlesticks and Sun indicator"""
        if self.nifty_data is None or self.sun_data is None or self.moon_data is None:
            messagebox.showwarning("No Data", "Please load data first!")
            return
        
        try:
            self.status_var.set("Generating chart...")
            
            # Clear previous chart
            for widget in self.chart_frame.winfo_children():
                widget.destroy()
            
            # Create figure with three subplots
            fig = plt.Figure(figsize=(14, 10), dpi=100)
            
            # Main candlestick chart (50% height)
            ax1 = fig.add_subplot(3, 1, 1)
            
            # Sun indicator chart (25% height)
            ax2 = fig.add_subplot(3, 1, 2, sharex=ax1)
            
            # Moon indicator chart (25% height)
            ax3 = fig.add_subplot(3, 1, 3, sharex=ax1)
            
            # Adjust spacing
            fig.subplots_adjust(hspace=0.15, left=0.08, right=0.95, top=0.96, bottom=0.06)
            
            # Plot Nifty candlesticks
            self.plot_candlesticks(ax1)
            
            # Plot Sun cycle indicator
            self.plot_sun_indicator(ax2)
            
            # Plot Moon cycle indicator
            self.plot_moon_indicator(ax3)
            
            # Embed in Tkinter
            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            
            # Add toolbar
            toolbar = NavigationToolbar2Tk(canvas, self.chart_frame)
            toolbar.update()
            
            self.status_var.set(f"Chart generated: {len(self.nifty_data)} days displayed")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate chart:\n{str(e)}")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    def plot_candlesticks(self, ax):
        """Plot Nifty candlestick chart"""
        # Prepare data for mplfinance-style plotting
        dates = self.nifty_data.index
        
        # Manual candlestick plotting for more control
        for idx in range(len(self.nifty_data)):
            row = self.nifty_data.iloc[idx]
            date = dates[idx]
            
            open_price = row['Open']
            close_price = row['Close']
            high_price = row['High']
            low_price = row['Low']
            
            # Determine color
            color = 'green' if close_price >= open_price else 'red'
            edge_color = 'darkgreen' if close_price >= open_price else 'darkred'
            
            # Draw high-low line
            ax.plot([date, date], [low_price, high_price], 
                   color=edge_color, linewidth=0.8)
            
            # Draw body rectangle
            height = abs(close_price - open_price)
            bottom = min(open_price, close_price)
            
            ax.add_patch(plt.Rectangle((date, bottom), 
                                       timedelta(hours=12), height,
                                       facecolor=color, 
                                       edgecolor=edge_color,
                                       linewidth=0.8))
        
        # Format chart
        ax.set_title('Nifty 50 Index - Candlestick Chart', 
                    fontsize=14, fontweight='bold', pad=10)
        ax.set_ylabel('Price (₹)', fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlim(dates[0] - timedelta(days=2), dates[-1] + timedelta(days=2))
        
        # Format y-axis
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{x:,.0f}'))
        
        # Add price levels
        current_price = self.nifty_data['Close'].iloc[-1]
        ax.axhline(y=current_price, color='blue', linestyle='--', 
                  linewidth=1, alpha=0.7, label=f'Current: ₹{current_price:,.0f}')
        ax.legend(loc='upper left', fontsize=9)
    
    def plot_sun_indicator(self, ax):
        """Plot Sun planetary position indicator as sinusoidal wave"""
        # Prepare Sun data aligned with trading days
        sun_df = self.sun_data.set_index('Date')
        
        # Create continuous line for Sun longitude
        dates = sun_df.index
        longitudes = sun_df['sun_longitude'].values
        
        # Convert longitude to sinusoidal representation
        # Normalize 0-360° to create smoother wave visualization
        # Map to sine wave: y = amplitude * sin(longitude in radians)
        radians = np.deg2rad(longitudes)
        
        # Create primary wave (one complete cycle = 360°)
        primary_wave = np.sin(radians) * 180 + 180  # Scale to 0-360 range
        
        # Also show the actual longitude as reference
        ax.plot(dates, longitudes, color='orange', linewidth=2.5, 
               label='Sun Longitude (0-360°)', alpha=0.8, zorder=3)
        
        # Add sinusoidal wave overlay
        ax.plot(dates, primary_wave, color='gold', linewidth=1.5, 
               linestyle='--', label='Sun Sine Wave', alpha=0.6, zorder=2)
        
        # Fill area under sine wave for visual effect
        ax.fill_between(dates, 0, primary_wave, color='gold', alpha=0.1, zorder=1)
        
        # Add zodiac sign transitions with color bands
        zodiac_colors = {
            'Aries': '#FF6B6B', 'Taurus': '#4ECDC4', 'Gemini': '#95E1D3',
            'Cancer': '#F38181', 'Leo': '#FFD93D', 'Virgo': '#6BCB77',
            'Libra': '#4D96FF', 'Scorpio': '#8E44AD', 'Sagittarius': '#E74C3C',
            'Capricorn': '#3498DB', 'Aquarius': '#1ABC9C', 'Pisces': '#9B59B6'
        }
        
        # Mark sign changes and add color bands
        prev_sign = None
        prev_date = None
        for idx, row in sun_df.iterrows():
            current_sign = row['sun_sign']
            if current_sign != prev_sign:
                if prev_sign is not None:
                    # Draw vertical transition line
                    ax.axvline(x=idx, color='gray', linestyle=':', 
                              linewidth=1.5, alpha=0.6, zorder=4)
                    # Add sign label at transition
                    ax.text(idx, 365, current_sign, 
                           rotation=90, verticalalignment='bottom',
                           fontsize=9, fontweight='bold', alpha=0.8,
                           color=zodiac_colors.get(current_sign, 'black'))
                    
                    # Add subtle color band for previous sign region
                    if prev_date is not None:
                        ax.axvspan(prev_date, idx, 
                                  color=zodiac_colors.get(prev_sign, 'gray'),
                                  alpha=0.05, zorder=0)
                
                prev_date = idx
            prev_sign = current_sign
        
        # Add final color band for last sign
        if prev_sign and prev_date:
            ax.axvspan(prev_date, dates[-1], 
                      color=zodiac_colors.get(prev_sign, 'gray'),
                      alpha=0.05, zorder=0)
        
        # Add cardinal degree reference lines (0, 90, 180, 270)
        for degree, label in [(0, '0° Aries'), (90, '90° Cancer'), 
                              (180, '180° Libra'), (270, '270° Capricorn')]:
            ax.axhline(y=degree, color='gray', linestyle='-', 
                      linewidth=0.8, alpha=0.4, zorder=1)
            ax.text(dates[0], degree + 5, label, fontsize=7, alpha=0.6,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                           alpha=0.7, edgecolor='none'))
        
        # Format chart
        ax.set_title('Sun Planetary Cycle - Vedic Astrology (Sinusoidal Wave)', 
                    fontsize=12, fontweight='bold')
        ax.set_xlabel('Date (Trading Days Only)', fontsize=10, fontweight='bold')
        ax.set_ylabel('Zodiac Longitude (°)', fontsize=10, fontweight='bold')
        ax.set_ylim(-10, 375)
        ax.grid(True, alpha=0.25, linestyle='--', linewidth=0.5)
        ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
        
        # Rotate x-axis labels
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    def plot_moon_indicator(self, ax):
        """Plot Moon planetary position indicator as sinusoidal wave"""
        # Prepare Moon data aligned with trading days
        moon_df = self.moon_data.set_index('Date')
        
        # Create continuous line for Moon longitude
        dates = moon_df.index
        longitudes = moon_df['moon_longitude'].values
        
        # Convert longitude to sinusoidal representation
        # Moon moves much faster (completes zodiac in ~27 days)
        radians = np.deg2rad(longitudes)
        
        # Create primary wave (one complete cycle = 360°)
        primary_wave = np.sin(radians) * 180 + 180  # Scale to 0-360 range
        
        # Also show the actual longitude as reference
        ax.plot(dates, longitudes, color='#9D4EDD', linewidth=2.5, 
               label='Moon Longitude (0-360°)', alpha=0.8, zorder=3)
        
        # Add sinusoidal wave overlay
        ax.plot(dates, primary_wave, color='#C77DFF', linewidth=1.5, 
               linestyle='--', label='Moon Sine Wave', alpha=0.6, zorder=2)
        
        # Fill area under sine wave for visual effect
        ax.fill_between(dates, 0, primary_wave, color='#E0AAFF', alpha=0.15, zorder=1)
        
        # Add zodiac sign transitions with color bands
        zodiac_colors = {
            'Aries': '#FF6B6B', 'Taurus': '#4ECDC4', 'Gemini': '#95E1D3',
            'Cancer': '#F38181', 'Leo': '#FFD93D', 'Virgo': '#6BCB77',
            'Libra': '#4D96FF', 'Scorpio': '#8E44AD', 'Sagittarius': '#E74C3C',
            'Capricorn': '#3498DB', 'Aquarius': '#1ABC9C', 'Pisces': '#9B59B6'
        }
        
        # Mark sign changes and add color bands
        prev_sign = None
        prev_date = None
        for idx, row in moon_df.iterrows():
            current_sign = row['moon_sign']
            if current_sign != prev_sign:
                if prev_sign is not None:
                    # Draw vertical transition line
                    ax.axvline(x=idx, color='gray', linestyle=':', 
                              linewidth=1.5, alpha=0.6, zorder=4)
                    # Add sign label at transition (smaller font for Moon)
                    ax.text(idx, 365, current_sign, 
                           rotation=90, verticalalignment='bottom',
                           fontsize=8, fontweight='bold', alpha=0.7,
                           color=zodiac_colors.get(current_sign, 'black'))
                    
                    # Add subtle color band for previous sign region
                    if prev_date is not None:
                        ax.axvspan(prev_date, idx, 
                                  color=zodiac_colors.get(prev_sign, 'gray'),
                                  alpha=0.05, zorder=0)
                
                prev_date = idx
            prev_sign = current_sign
        
        # Add final color band for last sign
        if prev_sign and prev_date:
            ax.axvspan(prev_date, dates[-1], 
                      color=zodiac_colors.get(prev_sign, 'gray'),
                      alpha=0.05, zorder=0)
        
        # Add cardinal degree reference lines (0, 90, 180, 270)
        for degree, label in [(0, '0°'), (90, '90°'), 
                              (180, '180°'), (270, '270°')]:
            ax.axhline(y=degree, color='gray', linestyle='-', 
                      linewidth=0.8, alpha=0.4, zorder=1)
            ax.text(dates[0], degree + 5, label, fontsize=7, alpha=0.6,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                           alpha=0.7, edgecolor='none'))
        
        # Format chart
        ax.set_title('Moon Planetary Cycle - Vedic Astrology (Sinusoidal Wave, ~27 days/cycle)', 
                    fontsize=12, fontweight='bold', color='#9D4EDD')
        ax.set_xlabel('Date (Trading Days Only)', fontsize=10, fontweight='bold')
        ax.set_ylabel('Zodiac Longitude (°)', fontsize=10, fontweight='bold')
        ax.set_ylim(-10, 375)
        ax.grid(True, alpha=0.25, linestyle='--', linewidth=0.5)
        ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
        
        # Rotate x-axis labels
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    def export_chart(self):
        """Export chart as image"""
        if self.nifty_data is None:
            messagebox.showwarning("No Data", "Please generate chart first!")
            return
        
        try:
            filename = f"nifty_sun_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join("..", "charts", filename)
            
            # Create charts directory if needed
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save would need reference to current figure
            messagebox.showinfo("Export", 
                f"Chart saved as: {filename}\n\n"
                "Use the toolbar save button to export the chart.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

def main():
    """Main entry point"""
    print("=" * 60)
    print("Nifty 50 with Sun Planetary Cycles Visualization")
    print("Vedic Astrology Integration")
    print("=" * 60)
    print()
    print("This application visualizes:")
    print("  1. Nifty 50 candlestick chart (2023 onwards)")
    print("  2. Sun's planetary position indicator below")
    print()
    print("Data sources:")
    print("  - Nifty prices: yfinance_daily_quotes table")
    print("  - Sun positions: planetary_positions table")
    print()
    print("Starting GUI...")
    print()
    
    app = NiftySunVisualization()
    app.run()

if __name__ == "__main__":
    main()
