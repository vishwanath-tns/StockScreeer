"""Trends analysis tab for the stock scanner GUI."""
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import threading
from typing import Optional

from services.trends_service import (
    scan_current_day_trends, scan_all_historical_trends, 
    get_trend_results, get_trend_summary_stats
)


class TrendsTab:
    def __init__(self, parent_frame, app):
        self.parent_frame = parent_frame
        self.app = app
        self.is_scanning = False
        self.scan_thread = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the trends tab UI."""
        # Main container
        main_frame = ttk.Frame(self.parent_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_frame, text="Trend Analysis Scanner", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Control panel
        control_frame = ttk.LabelFrame(main_frame, text="Scan Options", padding=10)
        control_frame.pack(fill='x', pady=(0, 10))
        
        # Button frame
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill='x')
        
        # Scan current day button
        self.current_day_btn = ttk.Button(button_frame, text="Scan Current Day Trends",
                                         command=self.scan_current_day)
        self.current_day_btn.pack(side='left', padx=(0, 10))
        
        # Scan all historical button
        self.historical_btn = ttk.Button(button_frame, text="Scan All Historical Data",
                                        command=self.scan_all_historical)
        self.historical_btn.pack(side='left', padx=(0, 10))
        
        # Scan all historical parallel button
        self.historical_parallel_btn = ttk.Button(button_frame, text="Scan All Historical (Fast)",
                                                 command=self.scan_all_historical_parallel)
        self.historical_parallel_btn.pack(side='left', padx=(0, 10))
        
        # Scan date range button
        self.date_range_btn = ttk.Button(button_frame, text="Scan Date Range",
                                        command=self.scan_historical_trends_range)
        self.date_range_btn.pack(side='left', padx=(0, 10))
        
        # Refresh results button
        self.refresh_btn = ttk.Button(button_frame, text="Refresh Results",
                                     command=self.refresh_results)
        self.refresh_btn.pack(side='left', padx=(0, 10))
        
        # Clear results button
        self.clear_btn = ttk.Button(button_frame, text="Clear Results",
                                   command=self.clear_results)
        self.clear_btn.pack(side='left')
        
        # Date range frame for historical analysis
        date_frame = ttk.LabelFrame(control_frame, text="Historical Scan Date Range", padding=5)
        date_frame.pack(fill='x', pady=(10, 5))
        
        # Start date
        ttk.Label(date_frame, text="Start Date:").grid(row=0, column=0, sticky='w', padx=(0, 5))
        self.start_date_var = tk.StringVar(value="2023-01-01")
        self.start_date_entry = ttk.Entry(date_frame, textvariable=self.start_date_var, width=12)
        self.start_date_entry.grid(row=0, column=1, padx=(0, 10))
        
        # End date
        ttk.Label(date_frame, text="End Date:").grid(row=0, column=2, sticky='w', padx=(0, 5))
        self.end_date_var = tk.StringVar(value="2025-12-31")
        self.end_date_entry = ttk.Entry(date_frame, textvariable=self.end_date_var, width=12)
        self.end_date_entry.grid(row=0, column=3, padx=(0, 10))
        
        # Stock symbol for individual analysis
        ttk.Label(date_frame, text="Symbol:").grid(row=0, column=4, sticky='w', padx=(0, 5))
        self.symbol_var = tk.StringVar()
        self.symbol_entry = ttk.Entry(date_frame, textvariable=self.symbol_var, width=12)
        self.symbol_entry.grid(row=0, column=5, padx=(0, 10))
        
        # View stock trend button
        self.view_stock_btn = ttk.Button(date_frame, text="View Stock Trend",
                                        command=self.view_stock_trend)
        self.view_stock_btn.grid(row=0, column=6, padx=(10, 0))
        
        # Chart stock button
        self.chart_stock_btn = ttk.Button(date_frame, text="Chart Stock",
                                         command=self.chart_stock)
        self.chart_stock_btn.grid(row=0, column=7, padx=(5, 0))
        
        # Progress frame
        progress_frame = ttk.Frame(control_frame)
        progress_frame.pack(fill='x', pady=(10, 0))
        
        # Progress bar
        self.progress_var = tk.StringVar(value="Ready")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.progress_label.pack(side='left')
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(side='right', fill='x', expand=True, padx=(10, 0))
        
        # Summary frame
        summary_frame = ttk.LabelFrame(main_frame, text="Summary Statistics", padding=10)
        summary_frame.pack(fill='x', pady=(0, 10))
        
        self.summary_text = tk.Text(summary_frame, height=4, state='disabled')
        self.summary_text.pack(fill='both', expand=True)
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Trend Analysis Results", padding=10)
        results_frame.pack(fill='both', expand=True)
        
        # Treeview for results
        columns = ('Symbol', 'Trade Date', 'Daily Trend', 'Weekly Trend', 
                  'Monthly Trend', 'Rating')
        
        self.tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=15)
        
        # Configure column headings and make them sortable
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_treeview(c))
            self.tree.column(col, width=100, anchor='center')
        
        # Adjust specific column widths
        self.tree.column('Symbol', width=80)
        self.tree.column('Trade Date', width=100)
        self.tree.column('Daily Trend', width=90)
        self.tree.column('Weekly Trend', width=90)
        self.tree.column('Monthly Trend', width=90)
        self.tree.column('Rating', width=60)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(results_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(results_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        
        # Configure tag colors for trends
        self.tree.tag_configure('positive', background='lightgreen')
        self.tree.tag_configure('negative', background='lightcoral')
        self.tree.tag_configure('neutral', background='lightyellow')
        
        # Load initial data
        self.refresh_results()
        self.update_summary()
    
    def sort_treeview(self, col):
        """Sort treeview by column."""
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        
        # Try to sort numerically if possible, otherwise sort as strings
        try:
            if col == 'Rating':
                data.sort(key=lambda x: int(x[0]), reverse=True)
            elif col == 'Trade Date':
                data.sort(key=lambda x: x[0], reverse=True)
            else:
                data.sort(key=lambda x: x[0])
        except ValueError:
            data.sort(key=lambda x: x[0])
        
        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)
    
    def scan_current_day(self):
        """Scan trends for current day."""
        if self.is_scanning:
            messagebox.showwarning("Scan in Progress", "A scan is already running. Please wait.")
            return
        
        self.is_scanning = True
        self.progress_var.set("Scanning current day trends...")
        self.progress_bar.start()
        self.current_day_btn.config(state='disabled')
        self.historical_btn.config(state='disabled')
        self.date_range_btn.config(state='disabled')
        
        def scan_worker():
            try:
                results_df = scan_current_day_trends()
                
                # Update UI in main thread
                self.parent_frame.after(0, lambda: self.scan_complete(results_df, "current day"))
                
            except Exception as e:
                self.parent_frame.after(0, lambda: self.scan_error(str(e)))
        
        self.scan_thread = threading.Thread(target=scan_worker, daemon=True)
        self.scan_thread.start()
    
    def scan_all_historical(self):
        """Scan trends for all historical data."""
        if self.is_scanning:
            messagebox.showwarning("Scan in Progress", "A scan is already running. Please wait.")
            return
        
        response = messagebox.askyesno(
            "Historical Scan", 
            "This will scan all historical data and may take a long time. Continue?"
        )
        if not response:
            return
        
        self.is_scanning = True
        self.progress_var.set("Scanning all historical data...")
        self.progress_bar.start()
        self.current_day_btn.config(state='disabled')
        self.historical_btn.config(state='disabled')
        self.date_range_btn.config(state='disabled')
        
        def scan_worker():
            try:
                def progress_callback(message):
                    self.parent_frame.after(0, lambda m=message: self.progress_var.set(m))
                
                total_processed = scan_all_historical_trends(progress_callback=progress_callback)
                
                # Update UI in main thread
                self.parent_frame.after(0, lambda: self.scan_complete(None, f"historical ({total_processed} records)"))
                
            except Exception as e:
                self.parent_frame.after(0, lambda: self.scan_error(str(e)))
        
        self.scan_thread = threading.Thread(target=scan_worker, daemon=True)
        self.scan_thread.start()
    
    def scan_all_historical_parallel(self):
        """Scan trends for all historical data using parallel processing."""
        if self.is_scanning:
            messagebox.showwarning("Scan in Progress", "A scan is already running. Please wait.")
            return
        
        response = messagebox.askyesno(
            "Parallel Historical Scan", 
            "This will scan all historical data using parallel processing for faster performance. Continue?"
        )
        if not response:
            return
        
        self.is_scanning = True
        self.progress_var.set("Starting parallel historical scan...")
        self.progress_bar.start()
        self.current_day_btn.config(state='disabled')
        self.historical_btn.config(state='disabled')
        self.historical_parallel_btn.config(state='disabled')
        self.date_range_btn.config(state='disabled')
        
        def scan_worker():
            try:
                def progress_callback(message):
                    self.parent_frame.after(0, lambda m=message: self.progress_var.set(m))
                
                # Import here to avoid circular import
                from services.trends_service import scan_all_historical_trends_parallel
                
                total_processed = scan_all_historical_trends_parallel(
                    max_workers=4, 
                    progress_callback=progress_callback
                )
                
                # Update UI in main thread
                self.parent_frame.after(0, lambda: self.scan_complete_parallel(total_processed))
                
            except Exception as e:
                self.parent_frame.after(0, lambda: self.scan_error(str(e)))
        
        self.scan_thread = threading.Thread(target=scan_worker, daemon=True)
        self.scan_thread.start()
    
    def scan_complete_parallel(self, total_processed: int):
        """Handle parallel scan completion."""
        self.is_scanning = False
        self.progress_bar.stop()
        self.progress_var.set(f"Completed parallel historical scan")
        self.current_day_btn.config(state='normal')
        self.historical_btn.config(state='normal')
        self.historical_parallel_btn.config(state='normal')
        self.date_range_btn.config(state='normal')
        
        self.refresh_results()
        self.update_summary()
        messagebox.showinfo("Scan Complete", f"Successfully completed parallel historical trend analysis ({total_processed} records processed).")
    
    def scan_complete(self, results_df: Optional[pd.DataFrame], scan_type: str):
        """Handle scan completion."""
        self.is_scanning = False
        self.progress_bar.stop()
        self.progress_var.set(f"Completed {scan_type} scan")
        self.current_day_btn.config(state='normal')
        self.historical_btn.config(state='normal')
        self.date_range_btn.config(state='normal')
        
        if results_df is not None:
            self.populate_results(results_df)
        else:
            self.refresh_results()
        
        self.update_summary()
        messagebox.showinfo("Scan Complete", f"Successfully completed {scan_type} trend analysis.")
    
    def scan_error(self, error_message: str):
        """Handle scan error."""
        self.is_scanning = False
        self.progress_bar.stop()
        self.progress_var.set("Scan failed")
        self.current_day_btn.config(state='normal')
        self.historical_btn.config(state='normal')
        self.historical_parallel_btn.config(state='normal')
        self.date_range_btn.config(state='normal')
        
        messagebox.showerror("Scan Error", f"Error during scan: {error_message}")
    
    def refresh_results(self):
        """Refresh the results display."""
        try:
            # Get latest 1000 results
            results_df = get_trend_results(limit=1000)
            self.populate_results(results_df)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh results: {e}")
    
    def clear_results(self):
        """Clear the results display."""
        for item in self.tree.get_children():
            self.tree.delete(item)
    
    def populate_results(self, df: pd.DataFrame):
        """Populate the treeview with results."""
        # Clear existing items
        self.clear_results()
        
        if df.empty:
            return
        
        # Insert new items
        for _, row in df.iterrows():
            # Determine tag based on rating
            rating = row['trend_rating']
            if rating > 0:
                tag = 'positive'
            elif rating < 0:
                tag = 'negative'
            else:
                tag = 'neutral'
            
            values = (
                row['symbol'],
                row['trade_date'].strftime('%Y-%m-%d') if hasattr(row['trade_date'], 'strftime') else str(row['trade_date']),
                row['daily_trend'],
                row['weekly_trend'],
                row['monthly_trend'],
                str(row['trend_rating'])
            )
            
            self.tree.insert('', 'end', values=values, tags=(tag,))
    
    def update_summary(self):
        """Update the summary statistics."""
        try:
            stats = get_trend_summary_stats()
            
            if not stats:
                summary_text = "No data available"
            else:
                # Provide default values for None results
                total_records = stats.get('total_records', 0) or 0
                unique_symbols = stats.get('unique_symbols', 0) or 0
                unique_dates = stats.get('unique_dates', 0) or 0
                avg_rating = stats.get('avg_rating', 0) or 0
                min_rating = stats.get('min_rating', 0) or 0
                max_rating = stats.get('max_rating', 0) or 0
                positive_ratings = stats.get('positive_ratings', 0) or 0
                negative_ratings = stats.get('negative_ratings', 0) or 0
                neutral_ratings = stats.get('neutral_ratings', 0) or 0
                
                summary_text = f"""Total Records: {total_records:,}
Unique Symbols: {unique_symbols:,} | Unique Dates: {unique_dates:,}
Average Rating: {avg_rating:.2f} | Range: {min_rating} to {max_rating}
Positive: {positive_ratings:,} | Negative: {negative_ratings:,} | Neutral: {neutral_ratings:,}"""
            
            self.summary_text.config(state='normal')
            self.summary_text.delete(1.0, tk.END)
            self.summary_text.insert(1.0, summary_text)
            self.summary_text.config(state='disabled')
            
        except Exception as e:
            print(f"Error updating summary: {e}")
    
    def view_stock_trend(self):
        """View trend analysis for a specific stock."""
        symbol = self.symbol_entry.get().strip().upper()
        if not symbol:
            messagebox.showwarning("Input Required", "Please enter a stock symbol")
            return
        
        try:
            # Import get_stock_trend_analysis function
            from services.trends_service import get_stock_trend_analysis
            
            results_df = get_stock_trend_analysis(symbol)
            if results_df is not None and not results_df.empty:
                self.populate_results(results_df)
                self.progress_var.set(f"Showing trends for {symbol}")
                messagebox.showinfo("Results", f"Found {len(results_df)} trend records for {symbol}")
            else:
                messagebox.showinfo("No Data", f"No trend data found for {symbol}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get trend data for {symbol}: {e}")
    
    def chart_stock(self):
        """Create and display a chart for the specified stock."""
        symbol = self.symbol_entry.get().strip().upper()
        if not symbol:
            messagebox.showwarning("Input Required", "Please enter a stock symbol")
            return
        
        try:
            # Import the chart window
            from chart_window import show_stock_chart
            
            # Show progress
            self.progress_var.set(f"Loading chart for {symbol}...")
            self.parent_frame.update()
            
            # Create and show the chart window
            chart_window = show_stock_chart(self.parent_frame, symbol, days=90)
            
            # Update progress
            self.progress_var.set(f"Chart opened for {symbol}")
            
        except Exception as e:
            messagebox.showerror("Chart Error", f"Failed to open chart for {symbol}: {e}")
            self.progress_var.set("Ready")
            print(f"Chart error: {e}")
    
    def scan_historical_trends_range(self):
        """Scan historical trends for a date range."""
        # Get date range
        start_date_str = self.start_date_entry.get().strip()
        end_date_str = self.end_date_entry.get().strip()
        
        if not start_date_str or not end_date_str:
            messagebox.showwarning("Input Required", "Please enter both start and end dates (YYYY-MM-DD)")
            return
        
        try:
            # Validate date format
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            if start_date > end_date:
                messagebox.showwarning("Invalid Range", "Start date must be before end date")
                return
            
            # Calculate number of trading days (rough estimate)
            delta = end_date - start_date
            estimated_days = delta.days
            
            # Confirm with user
            if not messagebox.askyesno("Confirm Scan", 
                f"This will scan trends for {estimated_days} days from {start_date} to {end_date}.\n"
                "This may take several minutes. Continue?"):
                return
            
            # Start background scan
            self.is_scanning = True
            self.progress_bar.start()
            self.progress_var.set("Scanning historical trends for date range...")
            self.current_day_btn.config(state='disabled')
            self.historical_btn.config(state='disabled')
            self.historical_parallel_btn.config(state='disabled')
            self.date_range_btn.config(state='disabled')
            
            def run_scan():
                try:
                    from services.trends_service import scan_historical_trends_for_range
                    results_df = scan_historical_trends_for_range(start_date, end_date)
                    self.parent_frame.after(0, lambda: self.scan_complete(results_df, "date range"))
                except Exception as e:
                    self.parent_frame.after(0, lambda: self.scan_error(str(e)))
            
            import threading
            threading.Thread(target=run_scan, daemon=True).start()
            
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter dates in YYYY-MM-DD format")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start date range scan: {e}")


def build_trends_tab(app) -> ttk.Frame:
    """Build and return the trends tab frame."""
    # Use the trends_frame that was already created in the ScannerGUI
    tab_frame = app.trends_frame
    trends_tab = TrendsTab(tab_frame, app)
    return tab_frame