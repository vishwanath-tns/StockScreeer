#!/usr/bin/env python3
"""
GUI-friendly chart viewer for stock trends.
"""

import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use('TkAgg')  # Ensure TkAgg backend for GUI integration
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import reporting_adv_decl as rad
from sqlalchemy import text

class StockChartWindow:
    """A dedicated window for displaying stock charts with trend ratings."""
    
    def __init__(self, parent, symbol, days=90):
        self.parent = parent
        self.symbol = symbol
        self.days = days
        
        # Create the window
        self.window = tk.Toplevel(parent)
        self.window.title(f"{symbol} - Stock Chart with Trend Ratings")
        self.window.geometry("1200x800")
        
        # Create the chart
        self.create_chart()
    
    def get_stock_data_with_ratings(self):
        """Get stock data with ratings for the chart."""
        engine = rad.engine()
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=self.days)
        
        with engine.connect() as conn:
            sql = text("""
            SELECT 
                p.trade_date,
                p.open_price,
                p.high_price,
                p.low_price,
                p.close_price,
                p.ttl_trd_qnty as volume,
                t.trend_rating,
                t.daily_trend,
                t.weekly_trend,
                t.monthly_trend
            FROM nse_equity_bhavcopy_full p
            LEFT JOIN trend_analysis t ON p.trade_date = t.trade_date AND p.symbol = t.symbol
            WHERE p.symbol = :symbol 
            AND p.series = 'EQ'
            AND p.trade_date >= :start_date
            AND p.trade_date <= :end_date
            ORDER BY p.trade_date
            """)
            
            df = pd.read_sql(sql, con=conn, params={
                'symbol': self.symbol,
                'start_date': start_date,
                'end_date': end_date
            })
            
            if not df.empty:
                df['trade_date'] = pd.to_datetime(df['trade_date'])
            
            return df
    
    def get_rating_color(self, rating):
        """Get color for rating."""
        if pd.isna(rating):
            return 'gray'
        elif rating >= 8:
            return '#00AA00'
        elif rating >= 5:
            return '#44CC44'
        elif rating >= 2:
            return '#88DD88'
        elif rating >= -2:
            return '#FFAA00'
        elif rating >= -5:
            return '#FF6666'
        elif rating >= -8:
            return '#CC3333'
        else:
            return '#AA0000'
    
    def create_chart(self):
        """Create the stock chart with trend ratings."""
        print(f"Creating chart for {self.symbol}...")
        
        # Get data
        df = self.get_stock_data_with_ratings()
        
        print(f"Data retrieved: {len(df)} rows")
        if not df.empty:
            print(f"Date range: {df['trade_date'].min()} to {df['trade_date'].max()}")
            print(f"Price range: {df['close_price'].min():.2f} to {df['close_price'].max():.2f}")
            print(f"Ratings available: {df['trend_rating'].notna().sum()} of {len(df)}")
        
        if df.empty:
            # Show error message
            error_label = tk.Label(self.window, text=f"No data found for {self.symbol}", 
                                 font=('Arial', 14))
            error_label.pack(expand=True)
            return
        
        # Create main frame first
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create matplotlib figure
        self.fig = Figure(figsize=(12, 8), dpi=100, facecolor='white')
        self.fig.tight_layout(pad=3.0)
        
        # Create subplots with proper spacing
        self.ax1 = self.fig.add_subplot(2, 1, 1)  # Price chart
        self.ax2 = self.fig.add_subplot(2, 1, 2)  # Ratings chart
        
        # Plot data with error handling
        try:
            self.plot_price_chart(df)
            print("Price chart plotted successfully")
        except Exception as e:
            print(f"Error plotting price chart: {e}")
        
        try:
            self.plot_ratings_chart(df)
            print("Ratings chart plotted successfully")
        except Exception as e:
            print(f"Error plotting ratings chart: {e}")
        
        # Charts now use continuous positioning - no need for date range sync
        
        # Create canvas and add to window
        self.canvas = FigureCanvasTkAgg(self.fig, master=main_frame)
        self.canvas.draw()
        
        # Pack canvas first
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add navigation toolbar
        toolbar = NavigationToolbar2Tk(self.canvas, main_frame)
        toolbar.update()
        
        # Add control panel
        self.create_control_panel(df)
    
    def plot_price_chart(self, df):
        """Plot the price chart (candlestick style) without weekend gaps."""
        self.ax1.clear()
        self.ax1.set_title(f'{self.symbol} - Stock Price with Trend Ratings', 
                          fontsize=14, fontweight='bold')
        
        # Ensure we have valid data
        if df.empty or 'close_price' not in df.columns:
            self.ax1.text(0.5, 0.5, 'No price data available', 
                         transform=self.ax1.transAxes, ha='center', va='center')
            return
        
        # Filter valid price data (no gaps)
        valid_price_data = df.dropna(subset=['open_price', 'high_price', 'low_price', 'close_price']).copy()
        if valid_price_data.empty:
            self.ax1.text(0.5, 0.5, 'No complete OHLC data available', 
                         transform=self.ax1.transAxes, ha='center', va='center')
            return
        
        # Sort by date to ensure proper order
        valid_price_data = valid_price_data.sort_values('trade_date').reset_index(drop=True)
        
        # Create continuous x-axis positions (0, 1, 2, 3...) to avoid weekend gaps
        x_positions = np.arange(len(valid_price_data))
        candle_width = 0.8  # Fixed width for consistent appearance
        
        print(f"Plotting {len(valid_price_data)} candlesticks continuously without weekend gaps")
        
        # Plot each candlestick using continuous positions
        from matplotlib.patches import Rectangle
        
        for i, (idx, row) in enumerate(valid_price_data.iterrows()):
            x_pos = x_positions[i]
            open_price = row['open_price']
            high_price = row['high_price']
            low_price = row['low_price']
            close_price = row['close_price']
            
            # Determine candle color (green for bullish, red for bearish)
            is_bullish = close_price >= open_price
            color = '#00AA00' if is_bullish else '#FF3333'
            edge_color = '#006600' if is_bullish else '#AA0000'
            
            # Draw high-low line (wick)
            self.ax1.plot([x_pos, x_pos], [low_price, high_price], 
                         color='black', linewidth=1, alpha=0.8)
            
            # Draw candle body (rectangle)
            body_height = abs(close_price - open_price)
            body_bottom = min(open_price, close_price)
            
            if body_height > 0:  # Avoid zero-height rectangles
                rect = Rectangle((x_pos - candle_width/2, body_bottom), 
                               candle_width, body_height,
                               facecolor=color, edgecolor=edge_color, 
                               linewidth=1, alpha=0.9)
                self.ax1.add_patch(rect)
            else:
                # Doji candle (open == close) - draw thin line
                self.ax1.plot([x_pos - candle_width/2, x_pos + candle_width/2], 
                             [close_price, close_price], 
                             color=edge_color, linewidth=2)
        
        # Format y-axis for prices
        self.ax1.set_ylabel('Price (₹)', fontsize=12)
        self.ax1.grid(True, alpha=0.3)
        
        # Custom x-axis labels showing dates but positioned continuously
        # Show every 5th date to avoid crowding
        step = max(1, len(valid_price_data) // 10)  # Show roughly 10 labels
        tick_positions = x_positions[::step]
        tick_labels = [valid_price_data.iloc[i]['trade_date'].strftime('%Y-%m-%d') 
                      for i in range(0, len(valid_price_data), step)]
        
        self.ax1.set_xticks(tick_positions)
        self.ax1.set_xticklabels(tick_labels, rotation=45, ha='right')
        
        # Set axis limits to show all candles without gaps
        self.ax1.set_xlim(-0.5, len(valid_price_data) - 0.5)
        
        # Format y-axis for price with currency symbol
        import matplotlib.pyplot as plt
        self.ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{x:.1f}'))
        
        # Set reasonable y-limits with padding
        price_min, price_max = valid_price_data['low_price'].min(), valid_price_data['high_price'].max()
        price_range = price_max - price_min
        self.ax1.set_ylim(price_min - price_range*0.05, price_max + price_range*0.05)
        
        # Store positions for ratings chart synchronization
        self.x_positions = x_positions
        self.valid_dates = valid_price_data['trade_date'].values
    
    def plot_ratings_chart(self, df):
        """Plot the ratings chart with continuous positioning (no weekend gaps)."""
        self.ax2.clear()
        self.ax2.set_title('Trend Ratings (-10 to +10)', fontsize=12)
        
        # Use synchronized positions from price chart if available
        if hasattr(self, 'x_positions') and hasattr(self, 'valid_dates'):
            # Match ratings to the same dates as price chart
            valid_price_data = df.dropna(subset=['open_price', 'high_price', 'low_price', 'close_price']).copy()
            valid_price_data = valid_price_data.sort_values('trade_date').reset_index(drop=True)
            
            if valid_price_data.empty:
                self.ax2.text(0.5, 0.5, 'No rating data available', 
                             transform=self.ax2.transAxes, ha='center', va='center')
                return
            
            # Get ratings for the same dates as price data
            ratings_data = []
            x_positions_with_ratings = []
            
            for i, (idx, row) in enumerate(valid_price_data.iterrows()):
                rating = row.get('trend_rating', None)
                if pd.notna(rating):
                    ratings_data.append(rating)
                    x_positions_with_ratings.append(i)
            
            if not ratings_data:
                self.ax2.text(0.5, 0.5, 'No trend rating data available', 
                             transform=self.ax2.transAxes, ha='center', va='center')
                return
            
            # Plot rating line using continuous positions
            self.ax2.plot(x_positions_with_ratings, ratings_data, 
                         color='purple', linewidth=3, marker='o', markersize=5, 
                         label='Trend Rating', markerfacecolor='white', markeredgewidth=2)
            
            # Add color background bars for rating zones
            for i, rating in enumerate(ratings_data):
                x_pos = x_positions_with_ratings[i]
                color = self.get_rating_color(rating)
                # Create background bars from -11 to +11
                self.ax2.bar(x_pos, 22, bottom=-11, color=color, alpha=0.15, 
                           width=0.8, edgecolor='none')
            
            # Use same x-axis ticks as price chart
            step = max(1, len(valid_price_data) // 10)
            tick_positions = list(range(0, len(valid_price_data), step))
            tick_labels = [valid_price_data.iloc[i]['trade_date'].strftime('%Y-%m-%d') 
                          for i in tick_positions]
            
            self.ax2.set_xticks(tick_positions)
            self.ax2.set_xticklabels(tick_labels, rotation=45, ha='right')
            
            # Set same x-axis limits as price chart
            self.ax2.set_xlim(-0.5, len(valid_price_data) - 0.5)
            
        else:
            # Fallback to original method if price chart not plotted yet
            valid_ratings = df.dropna(subset=['trend_rating'])
            if valid_ratings.empty:
                self.ax2.text(0.5, 0.5, 'No trend rating data available', 
                             transform=self.ax2.transAxes, ha='center', va='center')
                return
            
            # Use continuous positions for ratings too
            x_positions = np.arange(len(valid_ratings))
            self.ax2.plot(x_positions, valid_ratings['trend_rating'], 
                         color='purple', linewidth=3, marker='o', markersize=5, 
                         label='Trend Rating')
        
        # Add horizontal reference lines
        rating_levels = [10, 5, 2, 0, -2, -5, -10]
        rating_labels = ['Very Bullish', 'Bullish', 'Mod. Bull', 'Neutral', 
                        'Mod. Bear', 'Bearish', 'Very Bearish']
        
        for level, label in zip(rating_levels, rating_labels):
            color = self.get_rating_color(level)
            self.ax2.axhline(y=level, color=color, linestyle='--', alpha=0.7, linewidth=1.5)
        
        self.ax2.set_ylabel('Rating', fontsize=12)
        self.ax2.set_ylim(-11, 11)
        self.ax2.grid(True, alpha=0.3)
        
        # Show legend if we have ratings data
        if hasattr(self, 'x_positions') and len(x_positions_with_ratings) > 0:
            self.ax2.legend(loc='upper left')
        elif 'ratings_data' in locals() and ratings_data:
            self.ax2.legend(loc='upper left')
    
    def create_control_panel(self, df):
        """Create control panel with statistics."""
        control_frame = ttk.Frame(self.window)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Statistics
        if not df.empty:
            latest_price = df['close_price'].iloc[-1]
            price_change = ((df['close_price'].iloc[-1] / df['close_price'].iloc[0]) - 1) * 100
            
            valid_ratings = df.dropna(subset=['trend_rating'])
            if not valid_ratings.empty:
                latest_rating = valid_ratings['trend_rating'].iloc[-1]
                avg_rating = valid_ratings['trend_rating'].mean()
                
                stats_text = (f"Latest Price: ₹{latest_price:.2f} | "
                             f"Change: {price_change:+.1f}% | "
                             f"Latest Rating: {latest_rating:.1f} | "
                             f"Avg Rating: {avg_rating:.1f}")
            else:
                stats_text = f"Latest Price: ₹{latest_price:.2f} | Change: {price_change:+.1f}%"
            
            stats_label = ttk.Label(control_frame, text=stats_text, font=('Arial', 10))
            stats_label.pack(pady=5)
        
        # Close button
        close_btn = ttk.Button(control_frame, text="Close", command=self.window.destroy)
        close_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Export button
        export_btn = ttk.Button(control_frame, text="Save Chart", command=self.export_chart)
        export_btn.pack(side=tk.RIGHT)
    
    def export_chart(self):
        """Export chart to file."""
        try:
            import os
            os.makedirs('charts', exist_ok=True)
            
            filename = f"charts/{self.symbol}_trend_chart.png"
            self.fig.savefig(filename, dpi=300, bbox_inches='tight')
            
            # Show success message
            import tkinter.messagebox as messagebox
            messagebox.showinfo("Chart Saved", f"Chart saved to: {filename}")
            
        except Exception as e:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Save Error", f"Failed to save chart: {e}")

def show_stock_chart(parent, symbol, days=90):
    """Show stock chart in a new window."""
    return StockChartWindow(parent, symbol, days)

def test_chart_window():
    """Test the chart window."""
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    # Show chart for RELIANCE
    chart_window = StockChartWindow(root, "RELIANCE", 60)
    
    root.mainloop()

if __name__ == "__main__":
    test_chart_window()