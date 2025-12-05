import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import subprocess
from datetime import datetime

# Adjust path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mean_reversion.engine.scanner_engine import ScannerEngine
from utilities.nifty500_stocks_list import NIFTY_500_STOCKS

class MeanReversionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Mean Reversion Scanner (Event Driven)")
        self.root.geometry("1200x700")
        
        # Engine
        self.engine = ScannerEngine(num_workers=4)
        self.is_scanning = False
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#2c3e50")
        header.pack(fill="x", padx=0, pady=0)
        
        title = tk.Label(header, text="Mean Reversion Scanner", font=("Segoe UI", 20, "bold"), bg="#2c3e50", fg="white")
        title.pack(side="left", padx=20, pady=15)
        
        # Controls
        controls = tk.Frame(self.root)
        controls.pack(fill="x", padx=20, pady=10)
        
        self.btn_start = ttk.Button(controls, text="Start Scan", command=self.start_scan)
        self.btn_start.pack(side="left")
        
        self.btn_stop = ttk.Button(controls, text="Stop", command=self.stop_scan, state="disabled")
        self.btn_stop.pack(side="left", padx=10)
        
        self.lbl_status = tk.Label(controls, text="Ready. Double-click a row to view chart.", fg="gray")
        self.lbl_status.pack(side="left", padx=10)
        
        # Results Table Frame (for Scrollbar)
        table_frame = tk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        columns = ("symbol", "price", "signal", "strategy", "date", "details")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        self.tree.heading("symbol", text="Symbol")
        self.tree.heading("price", text="Price")
        self.tree.heading("signal", text="Signal")
        self.tree.heading("strategy", text="Strategy")
        self.tree.heading("date", text="Signal Date")
        self.tree.heading("details", text="Details")
        
        self.tree.column("symbol", width=100)
        self.tree.column("price", width=80)
        self.tree.column("signal", width=60)
        self.tree.column("strategy", width=120)
        self.tree.column("date", width=100)
        self.tree.column("details", width=400)
        
        # Tags for coloring
        self.tree.tag_configure('BUY', background='#e8f6e9') # Light Green
        self.tree.tag_configure('SELL', background='#ffebee') # Light Red
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Double Click Event
        self.tree.bind("<Double-1>", self.on_double_click)
        
    def start_scan(self):
        if self.is_scanning: return
        
        self.is_scanning = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.lbl_status.config(text="Scanning...", fg="blue")
        
        # Clear table
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Start Engine
        self.engine.start(NIFTY_500_STOCKS)
        
        # Schedule Polling
        self.root.after(500, self.poll_results)
        
    def stop_scan(self):
        self.engine.stop()
        self.is_scanning = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.lbl_status.config(text="Stopped", fg="red")
        
    def poll_results(self):
        if not self.is_scanning:
            return
            
        results = self.engine.get_results()
        for res in results:
            # Format Date
            date_str = ""
            if isinstance(res.timestamp, datetime) or hasattr(res.timestamp, 'strftime'):
                 date_str = res.timestamp.strftime('%Y-%m-%d')
            else:
                 date_str = str(res.timestamp)
                 
            self.tree.insert("", "end", values=(
                res.symbol,
                f"{res.last_price:.2f}",
                res.signal_type,
                res.strategy_name,
                date_str,
                str(res.details)
            ), tags=(res.signal_type,))
            self.tree.yview_moveto(1)
            
        # Continue polling
        self.root.after(500, self.poll_results)

    def on_double_click(self, event):
        item = self.tree.selection()[0]
        values = self.tree.item(item, "values")
        symbol = values[0]
        
        # Launch Chart Viewer
        script_path = os.path.join(os.path.dirname(__file__), "chart_viewer.py")
        subprocess.Popen([sys.executable, script_path, "--symbol", symbol])

if __name__ == "__main__":
    # Windows Multiprocessing support
    import multiprocessing
    multiprocessing.freeze_support()
    
    root = tk.Tk()
    app = MeanReversionGUI(root)
    root.mainloop()
