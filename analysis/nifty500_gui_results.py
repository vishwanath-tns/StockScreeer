#!/usr/bin/env python3
"""
Nifty 500 Momentum Results Viewer for GUI
Displays the latest Nifty 500 momentum scan results in a GUI-friendly format
"""

import pandas as pd
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.momentum.momentum_calculator import MomentumCalculator
try:
    from services.market_breadth_service import get_engine as get_database_engine
except ImportError:
    try:
        from db.connection import ensure_engine as get_database_engine
    except ImportError:
        print("Warning: Could not import database connection")
        get_database_engine = None

class Nifty500ResultsViewer:
    def __init__(self):
        self.calculator = MomentumCalculator()
        if get_database_engine:
            self.engine = get_database_engine()
        else:
            self.engine = None
        
    def get_latest_nifty500_results(self):
        """Get the latest Nifty 500 momentum results from database"""
        try:
            query = """
            SELECT 
                symbol,
                duration,
                momentum_pct,
                trend_direction,
                calculated_at
            FROM momentum_data 
            WHERE calculated_at >= %s
            AND symbol IN (
                SELECT DISTINCT symbol 
                FROM nse_equity_bhavcopy_full 
                WHERE series = 'EQ' 
                ORDER BY symbol
            )
            ORDER BY calculated_at DESC, symbol, 
                CASE duration 
                    WHEN '1W' THEN 1 
                    WHEN '1M' THEN 2 
                    WHEN '3M' THEN 3 
                    WHEN '6M' THEN 4 
                    WHEN '9M' THEN 5 
                    WHEN '12M' THEN 6 
                END
            """
            
            # Get data from last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params=[yesterday])
                
            if df.empty:
                return None, "No recent Nifty 500 momentum data found"
                
            return df, None
            
        except Exception as e:
            return None, f"Error fetching data: {str(e)}"
    
    def format_results_for_gui(self, df):
        """Format results for GUI display"""
        if df is None:
            return "No data available"
            
        # Pivot data to show all durations for each symbol
        pivot_df = df.pivot(index='symbol', columns='duration', values='momentum_pct')
        
        # Reorder columns
        duration_order = ['1W', '1M', '3M', '6M', '9M', '12M']
        available_durations = [d for d in duration_order if d in pivot_df.columns]
        pivot_df = pivot_df[available_durations]
        
        # Format percentages
        for col in pivot_df.columns:
            pivot_df[col] = pivot_df[col].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A")
        
        return pivot_df
    
    def create_gui_window(self):
        """Create a standalone GUI window for results"""
        # Get data
        df, error = self.get_latest_nifty500_results()
        
        if error:
            # Simple error dialog
            root = tk.Tk()
            root.title("Nifty 500 Results - Error")
            root.geometry("400x200")
            
            error_label = ttk.Label(root, text=error, wraplength=350)
            error_label.pack(pady=50)
            
            close_btn = ttk.Button(root, text="Close", command=root.destroy)
            close_btn.pack(pady=20)
            
            root.mainloop()
            return
        
        # Create main window
        root = tk.Tk()
        root.title("Nifty 500 Momentum Results")
        root.geometry("1000x700")
        
        # Create main frame
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_frame, text="Nifty 500 Momentum Analysis Results", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Stats
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        total_symbols = len(df['symbol'].unique())
        latest_time = df['calculated_at'].max()
        
        stats_text = f"Total Symbols: {total_symbols} | Latest Update: {latest_time}"
        stats_label = ttk.Label(stats_frame, text=stats_text)
        stats_label.pack()
        
        # Create treeview for results
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        
        # Treeview
        columns = ['Symbol'] + ['1W', '1M', '3M', '6M', '9M', '12M']
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                           yscrollcommand=v_scrollbar.set, 
                           xscrollcommand=h_scrollbar.set)
        
        # Configure scrollbars
        v_scrollbar.config(command=tree.yview)
        h_scrollbar.config(command=tree.xview)
        
        # Configure column headings
        tree.heading('Symbol', text='Symbol')
        tree.column('Symbol', width=100, anchor=tk.W)
        
        for col in columns[1:]:
            tree.heading(col, text=col)
            tree.column(col, width=80, anchor=tk.CENTER)
        
        # Format and insert data
        pivot_df = self.format_results_for_gui(df)
        
        for symbol, row in pivot_df.iterrows():
            values = [symbol] + [row.get(col, 'N/A') for col in columns[1:]]
            tree.insert('', tk.END, values=values)
        
        # Pack treeview and scrollbars
        tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        refresh_btn = ttk.Button(button_frame, text="Refresh Data", 
                                command=lambda: self.refresh_data(tree))
        refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        export_btn = ttk.Button(button_frame, text="Export to CSV", 
                               command=lambda: self.export_to_csv(pivot_df))
        export_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        close_btn = ttk.Button(button_frame, text="Close", command=root.destroy)
        close_btn.pack(side=tk.RIGHT)
        
        root.mainloop()
    
    def refresh_data(self, tree):
        """Refresh the data in the treeview"""
        # Clear current items
        for item in tree.get_children():
            tree.delete(item)
        
        # Get fresh data
        df, error = self.get_latest_nifty500_results()
        if error:
            return
        
        # Format and insert new data
        pivot_df = self.format_results_for_gui(df)
        columns = ['1W', '1M', '3M', '6M', '9M', '12M']
        
        for symbol, row in pivot_df.iterrows():
            values = [symbol] + [row.get(col, 'N/A') for col in columns]
            tree.insert('', tk.END, values=values)
    
    def export_to_csv(self, pivot_df):
        """Export results to CSV file"""
        try:
            filename = f"nifty500_momentum_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            pivot_df.to_csv(filename)
            print(f"Results exported to: {filename}")
        except Exception as e:
            print(f"Export error: {e}")

def main():
    """Main function to run the results viewer"""
    print("Loading Nifty 500 Momentum Results...")
    
    viewer = Nifty500ResultsViewer()
    viewer.create_gui_window()

if __name__ == "__main__":
    main()