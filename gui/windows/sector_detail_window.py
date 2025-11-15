"""
Sector Detail Window

Shows detailed stock analysis for a specific sector when double-clicking
from the sectoral analysis comparison table.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import sys
import os
from datetime import date

# Add parent directory to path for imports
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from services.market_breadth_service import get_sectoral_breadth

class SectorDetailWindow:
    def __init__(self, parent, sector_code, analysis_date=None):
        self.parent = parent
        self.sector_code = sector_code
        self.analysis_date = analysis_date
        self.window = None
        
        self.create_window()
        self.load_sector_data()
    
    def create_window(self):
        """Create the sector detail window."""
        self.window = tk.Toplevel(self.parent)
        self.window.title(f"📊 {self.sector_code} - Detailed Stock Analysis")
        self.window.geometry("1000x700")
        self.window.resizable(True, True)
        
        # Make window modal but handle parent properly
        try:
            self.window.transient(self.parent)
            self.window.grab_set()
        except:
            # If transient fails, just continue without it
            pass
        
        # Center the window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (1000 // 2)
        y = (self.window.winfo_screenheight() // 2) - (700 // 2)
        self.window.geometry(f"1000x700+{x}+{y}")
        
        # Create main frame
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title frame
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title = f"{self.sector_code.replace('NIFTY-', '')} SECTOR ANALYSIS"
        ttk.Label(title_frame, text=title, font=('Arial', 16, 'bold')).pack(side=tk.LEFT)
        
        # Date info
        date_str = self.analysis_date.strftime('%B %d, %Y') if self.analysis_date else "Latest"
        ttk.Label(title_frame, text=f"Analysis Date: {date_str}", 
                 font=('Arial', 12), foreground="blue").pack(side=tk.RIGHT)
        
        # Summary metrics frame
        self.setup_summary_frame(main_frame)
        
        # Stock details frame
        self.setup_stock_details_frame(main_frame)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(buttons_frame, text="Refresh Data", 
                  command=self.load_sector_data).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(buttons_frame, text="Export to CSV", 
                  command=self.export_to_csv).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(buttons_frame, text="Close", 
                  command=self.window.destroy).pack(side=tk.RIGHT)
    
    def setup_summary_frame(self, parent):
        """Create the summary metrics frame."""
        summary_frame = ttk.LabelFrame(parent, text="Sector Summary", padding=10)
        summary_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create grid for metrics
        self.metrics_frame = ttk.Frame(summary_frame)
        self.metrics_frame.pack(fill=tk.X)
        
        # Define metrics to display
        self.metric_labels = {}
        metrics = [
            ('total_stocks', 'Total Stocks', 0, 0, 'info'),
            ('bullish_count', 'Bullish Stocks', 0, 1, 'success'),
            ('bearish_count', 'Bearish Stocks', 0, 2, 'danger'),
            ('bullish_percent', 'Bullish %', 1, 0, 'success'),
            ('bearish_percent', 'Bearish %', 1, 1, 'danger'),
            ('daily_uptrend_percent', 'Daily Uptrend %', 1, 2, 'primary')
        ]
        
        for key, label, row, col, style in metrics:
            self.create_metric_widget(self.metrics_frame, key, label, row, col)
    
    def create_metric_widget(self, parent, key, label, row, col):
        """Create a metric display widget."""
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=col, padx=20, pady=10, sticky='nsew')
        parent.grid_columnconfigure(col, weight=1)
        
        # Label
        ttk.Label(frame, text=label, font=('Arial', 10, 'bold')).pack()
        
        # Value
        value_label = ttk.Label(frame, text="--", font=('Arial', 14, 'bold'))
        value_label.pack()
        self.metric_labels[key] = value_label
    
    def setup_stock_details_frame(self, parent):
        """Create the stock details frame with treeview."""
        details_frame = ttk.LabelFrame(parent, text="Individual Stock Analysis", padding=10)
        details_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview
        columns = ('Symbol', 'Trend Rating', 'Category', 'Daily Trend', 'Weekly Trend', 'Monthly Trend', 'Score')
        self.stock_tree = ttk.Treeview(details_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        col_widths = {'Symbol': 100, 'Trend Rating': 100, 'Category': 120, 
                     'Daily Trend': 100, 'Weekly Trend': 100, 'Monthly Trend': 100, 'Score': 80}
        
        for col in columns:
            self.stock_tree.heading(col, text=col, command=lambda _col=col: self.sort_stocks(_col))
            width = col_widths.get(col, 100)
            self.stock_tree.column(col, width=width, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.stock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status label
        self.status_label = ttk.Label(details_frame, text="Ready", foreground="blue")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
    
    def load_sector_data(self):
        """Load sector data from the database."""
        self.status_label.configure(text="🔄 Loading sector data...", foreground="orange")
        self.window.update()
        
        try:
            # Get sector data
            result = get_sectoral_breadth(self.sector_code, self.analysis_date)
            
            if not result or not result.get('success'):
                error_msg = result.get('error', 'Unknown error') if result else 'No data returned'
                self.status_label.configure(text=f"❌ Error: {error_msg}", foreground="red")
                return
            
            # Update summary metrics
            self.update_summary_metrics(result)
            
            # Update stock details
            self.update_stock_details(result)
            
            # Update status
            stock_count = result.get('total_stocks', 0)
            self.status_label.configure(text=f"✅ Loaded {stock_count} stocks", foreground="green")
            
        except Exception as e:
            self.status_label.configure(text=f"❌ Error loading data: {str(e)}", foreground="red")
    
    def update_summary_metrics(self, result):
        """Update the summary metrics display."""
        # Get summary data
        breadth_summary = result.get('breadth_summary', {})
        technical_breadth = result.get('technical_breadth', {})
        
        # Update metric labels
        self.metric_labels['total_stocks'].configure(text=str(result.get('total_stocks', 0)))
        self.metric_labels['bullish_count'].configure(text=str(breadth_summary.get('bullish_count', 0)))
        self.metric_labels['bearish_count'].configure(text=str(breadth_summary.get('bearish_count', 0)))
        
        # Format percentages
        bullish_pct = breadth_summary.get('bullish_percent', 0)
        bearish_pct = breadth_summary.get('bearish_percent', 0)
        daily_pct = technical_breadth.get('daily_uptrend_percent', 0)
        
        self.metric_labels['bullish_percent'].configure(text=f"{bullish_pct:.1f}%")
        self.metric_labels['bearish_percent'].configure(text=f"{bearish_pct:.1f}%")
        self.metric_labels['daily_uptrend_percent'].configure(text=f"{daily_pct:.1f}%")
        
        # Color code based on performance
        if bullish_pct >= 60:
            self.metric_labels['bullish_percent'].configure(foreground="green")
        elif bullish_pct >= 40:
            self.metric_labels['bullish_percent'].configure(foreground="orange")
        else:
            self.metric_labels['bullish_percent'].configure(foreground="red")
    
    def update_stock_details(self, result):
        """Update the stock details treeview."""
        # Clear existing data
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)
        
        # Get stock data
        sector_df = result.get('sector_data')
        if sector_df is None or sector_df.empty:
            return
        
        # Sort by trend rating (highest first)
        sector_df_sorted = sector_df.copy()
        # Ensure trend_rating is numeric
        sector_df_sorted['trend_rating'] = pd.to_numeric(sector_df_sorted['trend_rating'], errors='coerce').fillna(0)
        sector_df_sorted = sector_df_sorted.sort_values('trend_rating', ascending=False)
        
        # Add stocks to treeview
        for _, row in sector_df_sorted.iterrows():
            symbol = row.get('symbol', 'N/A')
            rating = row.get('trend_rating', 0)
            category = row.get('trend_category', 'N/A')
            daily = row.get('daily_trend', 'N/A')
            weekly = row.get('weekly_trend', 'N/A') 
            monthly = row.get('monthly_trend', 'N/A')
            
            # Calculate a simple score for ranking
            score = self.calculate_stock_score(rating, daily, weekly, monthly)
            
            values = [
                symbol,
                f"{rating:.1f}" if isinstance(rating, (int, float)) else str(rating),
                category,
                daily,
                weekly,
                monthly,
                f"{score:.1f}"
            ]
            
            # Insert with color coding
            item = self.stock_tree.insert('', tk.END, values=values)
            
            # Color code based on category
            if 'Very Bullish' in category:
                self.stock_tree.set(item, 'Symbol', f"🟢 {symbol}")
            elif 'Bullish' in category:
                self.stock_tree.set(item, 'Symbol', f"🟡 {symbol}")
            elif 'Bearish' in category:
                self.stock_tree.set(item, 'Symbol', f"🔴 {symbol}")
    
    def calculate_stock_score(self, rating, daily, weekly, monthly):
        """Calculate a composite score for stock ranking."""
        score = 0
        
        # Base score from trend rating
        if isinstance(rating, (int, float)):
            score += rating * 10
        
        # Bonus for positive trends
        trends = [daily, weekly, monthly]
        for trend in trends:
            if trend == 'UP':
                score += 5
            elif trend == 'DOWN':
                score -= 5
        
        return max(0, score)  # Ensure non-negative
    
    def sort_stocks(self, column):
        """Sort stocks by the selected column."""
        # Get all items
        items = [(self.stock_tree.set(item, column), item) for item in self.stock_tree.get_children('')]
        
        # Sort based on column type
        if column in ['Trend Rating', 'Score']:
            # Numeric sort
            items.sort(key=lambda x: float(x[0]) if x[0].replace('.', '').replace('-', '').isdigit() else 0, reverse=True)
        else:
            # String sort
            items.sort(key=lambda x: x[0])
        
        # Rearrange items
        for index, (val, item) in enumerate(items):
            self.stock_tree.move(item, '', index)
    
    def export_to_csv(self):
        """Export sector data to CSV file."""
        try:
            # Get sector data again
            result = get_sectoral_breadth(self.sector_code, self.analysis_date)
            
            if not result or not result.get('success'):
                messagebox.showerror("Export Error", "No data available to export")
                return
            
            sector_df = result.get('sector_data')
            if sector_df is None or sector_df.empty:
                messagebox.showerror("Export Error", "No stock data available to export")
                return
            
            # Create filename
            date_str = self.analysis_date.strftime('%Y%m%d') if self.analysis_date else 'latest'
            sector_name = self.sector_code.replace('NIFTY-', '')
            filename = f"reports/sectoral_analysis/{sector_name}_stocks_{date_str}.csv"
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            # Export to CSV
            sector_df.to_csv(filename, index=False)
            
            messagebox.showinfo("Export Success", f"Data exported to:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data:\n{str(e)}")