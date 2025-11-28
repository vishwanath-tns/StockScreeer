"""
Intraday 1-Minute Data Viewer
==============================

Interactive viewer for 1-minute candle data with advance-decline indicators.
Displays OHLCV data for selected stock with market breadth context.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os
from typing import List, Tuple

load_dotenv()


class Intraday1MinViewer:
    """Interactive viewer for 1-minute intraday data"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Intraday 1-Minute Data Viewer")
        self.root.geometry("1400x900")
        
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
        
        # Summary frame
        summary_frame = ttk.LabelFrame(self.root, text="Summary", padding="10")
        summary_frame.pack(fill=tk.X, side=tk.TOP, padx=10, pady=5)
        
        self.summary_label = ttk.Label(summary_frame, text="Select stock and date range to load data", font=('Arial', 10))
        self.summary_label.pack(anchor=tk.W)
        
        # Breadth indicator frame
        breadth_frame = ttk.LabelFrame(self.root, text="Market Breadth (Selected Period)", padding="10")
        breadth_frame.pack(fill=tk.X, side=tk.TOP, padx=10, pady=5)
        
        self.breadth_text = tk.Text(breadth_frame, height=6, wrap=tk.WORD, font=('Consolas', 9))
        self.breadth_text.pack(fill=tk.BOTH, expand=True)
        
        # Scrollable frame for data
        data_frame = ttk.LabelFrame(self.root, text="1-Minute Candle Data", padding="10")
        data_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create treeview with scrollbars
        tree_scroll_y = ttk.Scrollbar(data_frame, orient=tk.VERTICAL)
        tree_scroll_x = ttk.Scrollbar(data_frame, orient=tk.HORIZONTAL)
        
        self.tree = ttk.Treeview(
            data_frame,
            columns=('timestamp', 'open', 'high', 'low', 'close', 'volume', 'prev_close', 'change', 'change_pct', 'status'),
            show='headings',
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
            height=20
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
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
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
            
            # Display data
            self.display_data()
            self.display_breadth()
            self.update_summary()
            
            self.status_bar.config(text=f"Loaded {len(self.current_data)} candles")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")
            self.status_bar.config(text="Error loading data")
    
    def display_data(self):
        """Display candle data in treeview"""
        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add data rows
        for row in self.current_data:
            timestamp = row[0].strftime('%Y-%m-%d %H:%M:%S')
            open_price = f"{row[1]:.2f}" if row[1] else ""
            high_price = f"{row[2]:.2f}" if row[2] else ""
            low_price = f"{row[3]:.2f}" if row[3] else ""
            close_price = f"{row[4]:.2f}" if row[4] else ""
            volume = f"{row[5]:,}" if row[5] else ""
            prev_close = f"{row[6]:.2f}" if row[6] else ""
            change = f"{row[7]:+.2f}" if row[7] else ""
            change_pct = f"{row[8]:+.2f}%" if row[8] else ""
            status = row[9] if row[9] else ""
            
            # Color coding based on status
            tag = ''
            if status == 'ADVANCE':
                tag = 'green'
            elif status == 'DECLINE':
                tag = 'red'
            
            self.tree.insert('', tk.END, values=(
                timestamp, open_price, high_price, low_price, close_price,
                volume, prev_close, change, change_pct, status
            ), tags=(tag,))
        
        # Configure tags
        self.tree.tag_configure('green', foreground='green')
        self.tree.tag_configure('red', foreground='red')
    
    def display_breadth(self):
        """Display market breadth indicators"""
        self.breadth_text.delete('1.0', tk.END)
        
        if not self.current_breadth:
            self.breadth_text.insert('1.0', "No breadth data available for selected period")
            return
        
        # Calculate aggregate statistics
        total_snapshots = len(self.current_breadth)
        avg_advances = sum(row[1] for row in self.current_breadth) / total_snapshots
        avg_declines = sum(row[2] for row in self.current_breadth) / total_snapshots
        avg_adv_pct = sum(row[5] for row in self.current_breadth) / total_snapshots
        
        # Latest breadth
        latest = self.current_breadth[-1]
        
        text = f"Market Breadth Summary (Advance-Decline Indicators)\n"
        text += "=" * 70 + "\n\n"
        text += f"Period: {self.from_date_var.get()} to {self.to_date_var.get()}\n"
        text += f"Snapshots: {total_snapshots}\n\n"
        
        text += f"Latest Breadth ({latest[0].strftime('%Y-%m-%d %H:%M')}):\n"
        text += f"  Advances: {latest[1]:>6} ({latest[5]:>6.2f}%)  "
        text += f"Declines: {latest[2]:>6} ({latest[6]:>6.2f}%)  "
        text += f"Unchanged: {latest[3]:>6}\n"
        text += f"  A/D Ratio: {latest[7]:.2f}  " if latest[7] else "  A/D Ratio: N/A  "
        text += f"Difference: {latest[8]:+d}  "
        text += f"Sentiment: {latest[9]}\n\n"
        
        text += f"Period Average:\n"
        text += f"  Avg Advances: {avg_advances:.0f}  "
        text += f"Avg Declines: {avg_declines:.0f}  "
        text += f"Avg Advance %: {avg_adv_pct:.2f}%\n"
        
        self.breadth_text.insert('1.0', text)
    
    def update_summary(self):
        """Update summary information"""
        if not self.current_data:
            self.summary_label.config(text="No data found for selection")
            return
        
        stock = self.stock_var.get()
        num_candles = len(self.current_data)
        
        # Calculate statistics
        first_candle = self.current_data[0]
        last_candle = self.current_data[-1]
        
        open_price = first_candle[1]
        close_price = last_candle[4]
        high_price = max(row[2] for row in self.current_data if row[2])
        low_price = min(row[3] for row in self.current_data if row[3])
        total_volume = sum(row[5] for row in self.current_data if row[5])
        
        change = close_price - open_price
        change_pct = (change / open_price * 100) if open_price else 0
        
        summary = f"Stock: {stock}  |  Candles: {num_candles}  |  "
        summary += f"Period: {first_candle[0].strftime('%Y-%m-%d %H:%M')} to {last_candle[0].strftime('%Y-%m-%d %H:%M')}  |  "
        summary += f"Open: ₹{open_price:.2f}  Close: ₹{close_price:.2f}  "
        summary += f"High: ₹{high_price:.2f}  Low: ₹{low_price:.2f}  "
        summary += f"Change: ₹{change:+.2f} ({change_pct:+.2f}%)  "
        summary += f"Volume: {total_volume:,}"
        
        self.summary_label.config(text=summary)
    
    def export_to_csv(self):
        """Export current data to CSV file"""
        if not self.current_data:
            messagebox.showwarning("Warning", "No data to export")
            return
        
        try:
            stock = self.stock_var.get()
            from_date = self.from_date_var.get().replace('-', '')
            to_date = self.to_date_var.get().replace('-', '')
            
            filename = f"intraday_1min_{stock}_{from_date}_to_{to_date}.csv"
            
            with open(filename, 'w') as f:
                # Write header
                f.write("Timestamp,Open,High,Low,Close,Volume,Prev Close,Change,Change %,Status\n")
                
                # Write data
                for row in self.current_data:
                    timestamp = row[0].strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"{timestamp},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]},{row[6]},{row[7]},{row[8]},{row[9]}\n")
            
            messagebox.showinfo("Success", f"Data exported to {filename}")
            self.status_bar.config(text=f"Exported to {filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'engine'):
            self.engine.dispose()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = Intraday1MinViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
