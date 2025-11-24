"""
Intraday 1-Minute Data Viewer with Charts
==========================================

Interactive viewer for 1-minute candle data with candlestick charts and advance-decline line charts.
Displays OHLCV data for selected stock with market breadth context.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os
from typing import List, Tuple
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.dates as mdates

load_dotenv()


class Intraday1MinViewer:
    """Interactive viewer for 1-minute intraday data with charts"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Intraday 1-Minute Data Viewer - Charts Edition")
        self.root.geometry("1600x1000")
        
        # Database connection
        self.engine = self.create_db_engine()
        
        # Data cache
        self.available_stocks = []
        self.available_dates = []
        self.current_data = []
        self.current_breadth = []
        
        # Create UI
        self.create_ui()
        
        # Load initial data
        self.load_available_stocks()
        self.load_available_dates()
    
    def create_db_engine(self):
        """Create database engine"""
        url = URL.create(
            drivername="mysql+pymysql",
            username=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            database=os.getenv('MYSQL_DB', 'marketdata'),
            query={"charset": "utf8mb4"}
        )
        return create_engine(url, pool_pre_ping=True)
    
    def create_ui(self):
        """Create user interface"""
        # Top frame for controls
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X, side=tk.TOP)
        
        # Stock selection
        ttk.Label(control_frame, text="Stock:", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.stock_var = tk.StringVar()
        self.stock_combo = ttk.Combobox(control_frame, textvariable=self.stock_var, width=20, state='readonly')
        self.stock_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Date range
        ttk.Label(control_frame, text="From Date:", font=('Arial', 10, 'bold')).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.from_date_var = tk.StringVar()
        self.from_date_combo = ttk.Combobox(control_frame, textvariable=self.from_date_var, width=15, state='readonly')
        self.from_date_combo.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(control_frame, text="To Date:", font=('Arial', 10, 'bold')).grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.to_date_var = tk.StringVar()
        self.to_date_combo = ttk.Combobox(control_frame, textvariable=self.to_date_var, width=15, state='readonly')
        self.to_date_combo.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        
        # Load button
        self.load_btn = ttk.Button(control_frame, text="Load Data", command=self.load_data)
        self.load_btn.grid(row=0, column=6, padx=10, pady=5)
        
        # Export button
        self.export_btn = ttk.Button(control_frame, text="Export CSV", command=self.export_to_csv)
        self.export_btn.grid(row=0, column=7, padx=5, pady=5)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Tab 1: Charts
        self.chart_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.chart_tab, text="Charts")
        self.create_chart_tab()
        
        # Tab 2: Data Table
        self.data_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.data_tab, text="Data Table")
        self.create_data_tab()
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def create_chart_tab(self):
        """Create chart tab with matplotlib figures"""
        # Summary frame
        summary_frame = ttk.LabelFrame(self.chart_tab, text="Summary", padding="5")
        summary_frame.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)
        
        self.summary_label = ttk.Label(summary_frame, text="Select stock and date range to load data", font=('Arial', 10))
        self.summary_label.pack(anchor=tk.W)
        
        # Create matplotlib figure with three subplots (50% candlestick, 25% A-D diff, 25% A-D separate)
        self.fig = Figure(figsize=(14, 10), dpi=100)
        # Use gridspec for precise height ratios: 2:1:1 (50%:25%:25%)
        gs = self.fig.add_gridspec(3, 1, height_ratios=[2, 1, 1], hspace=0.3)
        self.ax_candle = self.fig.add_subplot(gs[0])  # Top 50% for candlesticks
        self.ax_breadth_diff = self.fig.add_subplot(gs[1])  # Middle 25% for A-D difference
        self.ax_breadth_separate = self.fig.add_subplot(gs[2])  # Bottom 25% for separate A-D lines
        
        # Embed matplotlib figure in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_tab)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add matplotlib toolbar
        toolbar_frame = ttk.Frame(self.chart_tab)
        toolbar_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()
    
    def create_data_tab(self):
        """Create data table tab"""
        # Breadth indicator frame
        breadth_frame = ttk.LabelFrame(self.data_tab, text="Market Breadth (Selected Period)", padding="5")
        breadth_frame.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)
        
        self.breadth_text = tk.Text(breadth_frame, height=6, wrap=tk.WORD, font=('Consolas', 9))
        self.breadth_text.pack(fill=tk.BOTH, expand=True)
        
        # Scrollable frame for data
        data_frame = ttk.LabelFrame(self.data_tab, text="1-Minute Candle Data", padding="5")
        data_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview with scrollbars
        tree_scroll_y = ttk.Scrollbar(data_frame, orient=tk.VERTICAL)
        tree_scroll_x = ttk.Scrollbar(data_frame, orient=tk.HORIZONTAL)
        
        self.tree = ttk.Treeview(
            data_frame,
            columns=('timestamp', 'open', 'high', 'low', 'close', 'volume', 'prev_close', 'change', 'change_pct', 'status'),
            show='headings',
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
            height=25
        )
        
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)
        
        # Define columns
        columns_config = [
            ('timestamp', 'Timestamp', 150),
            ('open', 'Open', 80),
            ('high', 'High', 80),
            ('low', 'Low', 80),
            ('close', 'Close', 80),
            ('volume', 'Volume', 100),
            ('prev_close', 'Prev Close', 90),
            ('change', 'Change', 80),
            ('change_pct', 'Change %', 90),
            ('status', 'Status', 100)
        ]
        
        for col, heading, width in columns_config:
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, anchor=tk.CENTER if col != 'timestamp' else tk.W)
        
        # Pack treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll_y.grid(row=0, column=1, sticky='ns')
        tree_scroll_x.grid(row=1, column=0, sticky='ew')
        
        data_frame.grid_rowconfigure(0, weight=1)
        data_frame.grid_columnconfigure(0, weight=1)
    
    def load_available_stocks(self):
        """Load list of available stocks"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT symbol 
                    FROM intraday_1min_candles 
                    ORDER BY symbol
                """))
                
                self.available_stocks = [row[0] for row in result]
                self.stock_combo['values'] = self.available_stocks
                
                if self.available_stocks:
                    # Set NIFTY as default if available, otherwise first stock
                    default_stock = 'NIFTY' if 'NIFTY' in self.available_stocks else self.available_stocks[0]
                    self.stock_combo.set(default_stock)
                
                self.status_bar.config(text=f"Loaded {len(self.available_stocks)} stocks")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load stocks: {e}")
    
    def load_available_dates(self):
        """Load list of available dates"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT trade_date 
                    FROM intraday_1min_candles 
                    ORDER BY trade_date DESC
                """))
                
                self.available_dates = [row[0].strftime('%Y-%m-%d') for row in result]
                self.from_date_combo['values'] = self.available_dates
                self.to_date_combo['values'] = self.available_dates
                
                if self.available_dates:
                    # Set date range to latest date by default
                    self.from_date_combo.set(self.available_dates[0])
                    self.to_date_combo.set(self.available_dates[0])
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load dates: {e}")
    
    def load_data(self):
        """Load 1-minute data for selected stock and date range"""
        stock = self.stock_var.get()
        from_date = self.from_date_var.get()
        to_date = self.to_date_var.get()
        
        if not stock or not from_date or not to_date:
            messagebox.showwarning("Warning", "Please select stock and date range")
            return
        
        try:
            self.status_bar.config(text="Loading data...")
            self.root.update()
            
            # Load candle data
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        candle_timestamp,
                        open_price,
                        high_price,
                        low_price,
                        close_price,
                        volume,
                        prev_close,
                        change_amt,
                        change_pct,
                        status
                    FROM intraday_1min_candles
                    WHERE symbol = :symbol
                      AND trade_date BETWEEN :from_date AND :to_date
                    ORDER BY candle_timestamp
                """), {'symbol': stock, 'from_date': from_date, 'to_date': to_date})
                
                self.current_data = result.fetchall()
            
            # Load breadth data for the same period
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        poll_time,
                        advances,
                        declines,
                        unchanged,
                        total_stocks,
                        adv_pct,
                        decl_pct,
                        adv_decl_ratio,
                        adv_decl_diff,
                        market_sentiment
                    FROM intraday_advance_decline
                    WHERE trade_date BETWEEN :from_date AND :to_date
                    ORDER BY poll_time
                """), {'from_date': from_date, 'to_date': to_date})
                
                self.current_breadth = result.fetchall()
            
            # Update displays
            self.update_summary()
            self.update_breadth_display()
            self.update_data_table()
            self.update_charts()
            
            self.status_bar.config(text=f"Loaded {len(self.current_data)} candles")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")
            import traceback
            traceback.print_exc()
            self.status_bar.config(text="Error loading data")
    
    def update_summary(self):
        """Update summary information"""
        if not self.current_data:
            self.summary_label.config(text="No data available for the selected period")
            return
        
        stock = self.stock_var.get()
        num_candles = len(self.current_data)
        
        if num_candles > 0:
            first_candle = self.current_data[0]
            last_candle = self.current_data[-1]
            
            open_price = float(first_candle[1])
            high_price = max(float(c[2]) for c in self.current_data)
            low_price = min(float(c[3]) for c in self.current_data)
            close_price = float(last_candle[4])
            total_volume = sum(int(c[5]) for c in self.current_data)
            
            change = close_price - open_price
            change_pct = (change / open_price * 100) if open_price else 0
            
            summary = (
                f"{stock} | Candles: {num_candles} | "
                f"O: {open_price:.2f} | H: {high_price:.2f} | L: {low_price:.2f} | C: {close_price:.2f} | "
                f"Change: {change:+.2f} ({change_pct:+.2f}%) | Vol: {total_volume:,}"
            )
            self.summary_label.config(text=summary)
    
    def update_breadth_display(self):
        """Update breadth indicator text display"""
        self.breadth_text.delete('1.0', tk.END)
        
        if not self.current_breadth:
            self.breadth_text.insert('1.0', "No market breadth data available for the selected period")
            return
        
        # Calculate aggregate stats
        total_advances = sum(int(row[1]) for row in self.current_breadth)
        total_declines = sum(int(row[2]) for row in self.current_breadth)
        total_unchanged = sum(int(row[3]) for row in self.current_breadth)
        num_samples = len(self.current_breadth)
        
        avg_advances = total_advances / num_samples if num_samples else 0
        avg_declines = total_declines / num_samples if num_samples else 0
        avg_adv_pct = sum(float(row[5]) for row in self.current_breadth) / num_samples if num_samples else 0
        avg_decl_pct = sum(float(row[6]) for row in self.current_breadth) / num_samples if num_samples else 0
        
        # Determine overall sentiment
        if avg_adv_pct > 60:
            sentiment = "STRONG ADVANCE"
            sentiment_color = "green"
        elif avg_adv_pct > 52:
            sentiment = "ADVANCE"
            sentiment_color = "dark green"
        elif avg_decl_pct > 60:
            sentiment = "STRONG DECLINE"
            sentiment_color = "red"
        elif avg_decl_pct > 52:
            sentiment = "DECLINE"
            sentiment_color = "dark red"
        else:
            sentiment = "NEUTRAL"
            sentiment_color = "black"
        
        text = f"""Market Breadth Summary ({num_samples} samples):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Average Advances:  {avg_advances:>8.1f} ({avg_adv_pct:>6.2f}%)
Average Declines:  {avg_declines:>8.1f} ({avg_decl_pct:>6.2f}%)
Net Difference:    {avg_advances - avg_declines:>8.1f}
Overall Sentiment: {sentiment}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        self.breadth_text.insert('1.0', text)
        self.breadth_text.tag_add("sentiment", "6.19", "6.end")
        self.breadth_text.tag_config("sentiment", foreground=sentiment_color, font=('Consolas', 9, 'bold'))
    
    def update_data_table(self):
        """Update data table with current data"""
        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not self.current_data:
            return
        
        # Insert data
        for row in self.current_data:
            timestamp, open_p, high, low, close, volume, prev_close, change, change_pct, status = row
            
            # Determine color based on close vs open
            if close > open_p:
                tag = 'green'
            elif close < open_p:
                tag = 'red'
            else:
                tag = 'black'
            
            # Format values
            values = (
                timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                f"{float(open_p):.2f}",
                f"{float(high):.2f}",
                f"{float(low):.2f}",
                f"{float(close):.2f}",
                f"{int(volume):,}",
                f"{float(prev_close):.2f}" if prev_close else "N/A",
                f"{float(change):+.2f}" if change else "N/A",
                f"{float(change_pct):+.2f}%" if change_pct else "N/A",
                status if status else "N/A"
            )
            
            self.tree.insert('', tk.END, values=values, tags=(tag,))
        
        # Configure tags
        self.tree.tag_configure('green', foreground='#006400')
        self.tree.tag_configure('red', foreground='#8B0000')
        self.tree.tag_configure('black', foreground='#000000')
    
    def update_charts(self):
        """Update candlestick and breadth line charts"""
        if not self.current_data:
            self.ax_candle.clear()
            self.ax_breadth_diff.clear()
            self.ax_breadth_separate.clear()
            self.ax_candle.text(0.5, 0.5, 'No data to display', ha='center', va='center', transform=self.ax_candle.transAxes)
            self.ax_breadth_diff.text(0.5, 0.5, 'No data to display', ha='center', va='center', transform=self.ax_breadth_diff.transAxes)
            self.ax_breadth_separate.text(0.5, 0.5, 'No data to display', ha='center', va='center', transform=self.ax_breadth_separate.transAxes)
            self.canvas.draw()
            return
        
        try:
            # Clear previous plots
            self.ax_candle.clear()
            self.ax_breadth_diff.clear()
            self.ax_breadth_separate.clear()
            
            # Prepare candle data
            timestamps = [row[0] for row in self.current_data]
            opens = [float(row[1]) for row in self.current_data]
            highs = [float(row[2]) for row in self.current_data]
            lows = [float(row[3]) for row in self.current_data]
            closes = [float(row[4]) for row in self.current_data]
            
            # Plot candlesticks
            for i, (ts, o, h, l, c) in enumerate(zip(timestamps, opens, highs, lows, closes)):
                color = '#00AA00' if c >= o else '#CC0000'
                # Draw high-low line (wick)
                self.ax_candle.plot([i, i], [l, h], color='black', linewidth=1)
                # Draw candlestick body
                height = abs(c - o) if abs(c - o) > 0 else 0.01  # Minimum height for doji
                bottom = min(o, c)
                self.ax_candle.bar(i, height, bottom=bottom, width=0.8, color=color, edgecolor='black', linewidth=0.5)
            
            # Configure candlestick chart
            stock = self.stock_var.get()
            from_date = self.from_date_var.get()
            to_date = self.to_date_var.get()
            self.ax_candle.set_ylabel('Price (₹)', fontsize=11, fontweight='bold')
            self.ax_candle.set_title(f'{stock} - 1-Minute Candlestick Chart ({from_date} to {to_date})', 
                                    fontsize=13, fontweight='bold', pad=10)
            self.ax_candle.grid(True, alpha=0.3, linestyle='--')
            self.ax_candle.set_xlim(-1, len(timestamps))
            
            # Set x-axis labels for candlestick chart (time only)
            num_labels = min(15, len(timestamps))
            if num_labels > 0:
                step = max(1, len(timestamps) // num_labels)
                tick_positions = list(range(0, len(timestamps), step))
                tick_labels = [timestamps[i].strftime('%H:%M') for i in tick_positions]
                self.ax_candle.set_xticks(tick_positions)
                self.ax_candle.set_xticklabels([])  # Hide x-labels on top chart
            
            # Plot advance-decline charts
            if self.current_breadth:
                breadth_times = [row[0] for row in self.current_breadth]
                advances = [int(row[1]) for row in self.current_breadth]
                declines = [int(row[2]) for row in self.current_breadth]
                ad_diff = [adv - dec for adv, dec in zip(advances, declines)]
                
                # Create x-axis positions for breadth data
                breadth_x = list(range(len(ad_diff)))
                
                # ========== CHART 1: Advance-Decline Difference ==========
                self.ax_breadth_diff.plot(breadth_x, ad_diff, color='#0066CC', linewidth=2.5, label='Advance - Decline', marker='o', markersize=3)
                self.ax_breadth_diff.axhline(y=0, color='gray', linestyle='--', linewidth=1.5, alpha=0.7)
                
                # Fill areas
                self.ax_breadth_diff.fill_between(breadth_x, ad_diff, 0, 
                                             where=[x >= 0 for x in ad_diff],
                                             color='#00AA00', alpha=0.3, label='Net Advance')
                self.ax_breadth_diff.fill_between(breadth_x, ad_diff, 0,
                                             where=[x < 0 for x in ad_diff],
                                             color='#CC0000', alpha=0.3, label='Net Decline')
                
                # Configure difference chart
                self.ax_breadth_diff.set_ylabel('A-D Difference', fontsize=10, fontweight='bold')
                self.ax_breadth_diff.set_title('Market Breadth: Net Advance-Decline', 
                                         fontsize=12, fontweight='bold', pad=8)
                self.ax_breadth_diff.grid(True, alpha=0.3, linestyle='--')
                self.ax_breadth_diff.legend(loc='upper left', fontsize=9, framealpha=0.9)
                self.ax_breadth_diff.set_xlim(-1, len(breadth_x))
                self.ax_breadth_diff.set_xticklabels([])  # Hide x-labels on middle chart
                
                # ========== CHART 2: Separate Advances and Declines Lines ==========
                self.ax_breadth_separate.plot(breadth_x, advances, color='#00AA00', linewidth=2.5, 
                                             label='Advances', marker='o', markersize=3)
                self.ax_breadth_separate.plot(breadth_x, declines, color='#CC0000', linewidth=2.5, 
                                             label='Declines', marker='s', markersize=3)
                
                # Configure separate lines chart
                self.ax_breadth_separate.set_xlabel('Time', fontsize=11, fontweight='bold')
                self.ax_breadth_separate.set_ylabel('Stock Count', fontsize=10, fontweight='bold')
                self.ax_breadth_separate.set_title('Market Breadth: Advances vs Declines (Separate)', 
                                         fontsize=12, fontweight='bold', pad=8)
                self.ax_breadth_separate.grid(True, alpha=0.3, linestyle='--')
                self.ax_breadth_separate.legend(loc='upper left', fontsize=9, framealpha=0.9)
                self.ax_breadth_separate.set_xlim(-1, len(breadth_x))
                
                # Set x-axis labels for bottom chart only
                num_breadth_labels = min(15, len(breadth_times))
                if num_breadth_labels > 0:
                    step = max(1, len(breadth_times) // num_breadth_labels)
                    tick_positions = list(range(0, len(breadth_times), step))
                    tick_labels = [breadth_times[i].strftime('%H:%M') for i in tick_positions]
                    self.ax_breadth_separate.set_xticks(tick_positions)
                    self.ax_breadth_separate.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=9)
            else:
                self.ax_breadth_diff.text(0.5, 0.5, 'No market breadth data available', 
                                    ha='center', va='center', transform=self.ax_breadth_diff.transAxes, fontsize=12)
                self.ax_breadth_separate.text(0.5, 0.5, 'No market breadth data available', 
                                    ha='center', va='center', transform=self.ax_breadth_separate.transAxes, fontsize=12)
            
            # Adjust layout and redraw
            self.fig.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error updating charts: {e}")
            import traceback
            traceback.print_exc()
    
    def export_to_csv(self):
        """Export current data to CSV"""
        if not self.current_data:
            messagebox.showwarning("Warning", "No data to export")
            return
        
        try:
            # Ask for file location
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"{self.stock_var.get()}_{self.from_date_var.get()}_{self.to_date_var.get()}.csv"
            )
            
            if not filename:
                return
            
            # Write to CSV
            with open(filename, 'w') as f:
                # Header
                f.write("Timestamp,Open,High,Low,Close,Volume,Prev Close,Change,Change %,Status\n")
                
                # Data rows
                for row in self.current_data:
                    timestamp, open_p, high, low, close, volume, prev_close, change, change_pct, status = row
                    f.write(f"{timestamp},{open_p},{high},{low},{close},{volume},{prev_close or ''},{change or ''},{change_pct or ''},{status or ''}\n")
            
            messagebox.showinfo("Success", f"Data exported to {filename}")
            self.status_bar.config(text=f"Exported {len(self.current_data)} rows to CSV")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = Intraday1MinViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
