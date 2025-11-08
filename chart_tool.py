#!/usr/bin/env python3
"""
Simple standalone chart tool for testing.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from chart_window import show_stock_chart

class SimpleChartTool:
    """Simple GUI for creating stock charts."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Stock Chart Tool with Trend Ratings")
        self.root.geometry("400x200")
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create the GUI widgets."""
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Stock Chart with Trend Ratings", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Symbol input
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(input_frame, text="Stock Symbol:").pack(side=tk.LEFT)
        self.symbol_var = tk.StringVar(value="RELIANCE")
        self.symbol_entry = ttk.Entry(input_frame, textvariable=self.symbol_var, width=15)
        self.symbol_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Days input
        days_frame = ttk.Frame(main_frame)
        days_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(days_frame, text="Days:").pack(side=tk.LEFT)
        self.days_var = tk.StringVar(value="90")
        self.days_entry = ttk.Entry(days_frame, textvariable=self.days_var, width=10)
        self.days_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        self.chart_btn = ttk.Button(button_frame, text="Create Chart", 
                                   command=self.create_chart)
        self.chart_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.quit_btn = ttk.Button(button_frame, text="Quit", 
                                  command=self.root.quit)
        self.quit_btn.pack(side=tk.RIGHT)
        
        # Status
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_label.pack(pady=(10, 0))
        
        # Popular stocks
        popular_frame = ttk.LabelFrame(main_frame, text="Popular Stocks", padding=10)
        popular_frame.pack(fill=tk.X, pady=(20, 0))
        
        popular_stocks = ["RELIANCE", "TCS", "SBIN", "INFY", "HDFCBANK", "ICICIBANK"]
        for i, stock in enumerate(popular_stocks):
            btn = ttk.Button(popular_frame, text=stock, width=10,
                           command=lambda s=stock: self.quick_chart(s))
            btn.grid(row=i//3, column=i%3, padx=5, pady=2)
    
    def create_chart(self):
        """Create chart for entered symbol."""
        symbol = self.symbol_var.get().strip().upper()
        if not symbol:
            messagebox.showwarning("Input Required", "Please enter a stock symbol")
            return
        
        try:
            days = int(self.days_var.get())
            if days <= 0:
                raise ValueError("Days must be positive")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number of days")
            return
        
        self.show_chart(symbol, days)
    
    def quick_chart(self, symbol):
        """Create chart for a popular stock."""
        self.symbol_var.set(symbol)
        days = int(self.days_var.get())
        self.show_chart(symbol, days)
    
    def show_chart(self, symbol, days):
        """Show the chart window."""
        try:
            self.status_var.set(f"Loading chart for {symbol}...")
            self.root.update()
            
            # Create chart window
            chart_window = show_stock_chart(self.root, symbol, days)
            
            self.status_var.set(f"Chart opened for {symbol}")
            
        except Exception as e:
            messagebox.showerror("Chart Error", f"Failed to create chart for {symbol}: {e}")
            self.status_var.set("Error creating chart")
            print(f"Chart error: {e}")
    
    def run(self):
        """Run the application."""
        self.root.mainloop()

def main():
    """Main function."""
    app = SimpleChartTool()
    app.run()

if __name__ == "__main__":
    main()