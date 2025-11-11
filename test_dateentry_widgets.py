#!/usr/bin/env python3
"""
Test script to debug Market Breadth date range UI issue
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

# Add the project path
sys.path.append('d:/MyProjects/StockScreeer')

# Test tkcalendar import
try:
    from tkcalendar import DateEntry
    print("✅ tkcalendar import successful")
except ImportError as e:
    print(f"❌ tkcalendar import failed: {e}")
    sys.exit(1)

def test_dateentry_widget():
    """Test if DateEntry widgets work properly"""
    print("🧪 Testing DateEntry widget creation...")
    
    root = tk.Tk()
    root.title("DateEntry Test")
    root.geometry("600x400")
    
    # Create a frame to test the exact same setup as market breadth
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Date Range Analysis Frame (exactly like in market_breadth.py)
    range_frame = ttk.LabelFrame(main_frame, text="Market Depth Analysis - Date Range", padding=10)
    range_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
    
    # Calculate default dates (last 30 days)
    from datetime import datetime, timedelta
    end_default = datetime.now().date()
    start_default = end_default - timedelta(days=30)
    
    # Start date
    start_date_frame = ttk.Frame(range_frame)
    start_date_frame.pack(side=tk.LEFT, padx=(0, 10))
    ttk.Label(start_date_frame, text="Start Date:").pack(anchor=tk.W)
    start_date_picker = DateEntry(start_date_frame, width=12, background='darkblue',
                                 foreground='white', borderwidth=2, date_pattern='dd/mm/yyyy')
    start_date_picker.set_date(start_default)
    start_date_picker.pack()
    
    # End date
    end_date_frame = ttk.Frame(range_frame)
    end_date_frame.pack(side=tk.LEFT, padx=(0, 10))
    ttk.Label(end_date_frame, text="End Date:").pack(anchor=tk.W)
    end_date_picker = DateEntry(end_date_frame, width=12, background='darkblue',
                               foreground='white', borderwidth=2, date_pattern='dd/mm/yyyy')
    end_date_picker.set_date(end_default)
    end_date_picker.pack()
    
    # Analyze range button
    def test_button_click():
        start_date = start_date_picker.get_date()
        end_date = end_date_picker.get_date()
        print(f"📅 Selected range: {start_date} to {end_date}")
        messagebox.showinfo("Date Range", f"Selected: {start_date} to {end_date}")
    
    analyze_range_btn = ttk.Button(range_frame, text="Analyze Date Range", 
                                  command=test_button_click)
    analyze_range_btn.pack(side=tk.LEFT, padx=(10, 0))
    
    # Range status label
    range_status_label = ttk.Label(range_frame, text="Select date range for analysis", 
                                  foreground="blue")
    range_status_label.pack(side=tk.LEFT, padx=(10, 0))
    
    # Add some debug info
    debug_frame = ttk.Frame(main_frame)
    debug_frame.pack(fill=tk.X, pady=10)
    
    ttk.Label(debug_frame, text="✅ If you can see date pickers above, they work correctly!", 
             foreground="green", font=('Arial', 12, 'bold')).pack()
    
    print("🎯 Test window created. Check if date pickers are visible...")
    root.mainloop()

if __name__ == "__main__":
    test_dateentry_widget()