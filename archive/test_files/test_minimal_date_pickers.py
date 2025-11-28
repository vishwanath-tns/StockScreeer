#!/usr/bin/env python3
"""
Minimal test to ensure date picker components are visible
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

# Add the project path
sys.path.append('d:/MyProjects/StockScreeer')

def minimal_date_picker_test():
    """Minimal test with explicit visibility checks"""
    print("🧪 Minimal Date Picker Test...")
    
    root = tk.Tk()
    root.title("Date Picker Visibility Test")
    root.geometry("800x400")
    
    # Create main frame
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Test without tkcalendar first (fallback)
    fallback_frame = ttk.LabelFrame(main_frame, text="Standard Entry Test", padding=10)
    fallback_frame.pack(fill=tk.X, pady=(0, 10))
    
    ttk.Label(fallback_frame, text="Start Date (YYYY-MM-DD):").pack(side=tk.LEFT)
    start_entry = ttk.Entry(fallback_frame, width=12)
    start_entry.insert(0, "2025-10-11")
    start_entry.pack(side=tk.LEFT, padx=(5, 10))
    
    ttk.Label(fallback_frame, text="End Date (YYYY-MM-DD):").pack(side=tk.LEFT)
    end_entry = ttk.Entry(fallback_frame, width=12)
    end_entry.insert(0, "2025-11-10")
    end_entry.pack(side=tk.LEFT, padx=(5, 10))
    
    def test_fallback():
        start_val = start_entry.get()
        end_val = end_entry.get()
        result_label.config(text=f"Fallback: {start_val} to {end_val}")
    
    ttk.Button(fallback_frame, text="Test Fallback", command=test_fallback).pack(side=tk.LEFT, padx=(10, 0))
    
    # Test with tkcalendar
    try:
        from tkcalendar import DateEntry
        from datetime import datetime, timedelta
        
        dateentry_frame = ttk.LabelFrame(main_frame, text="DateEntry Test", padding=10)
        dateentry_frame.pack(fill=tk.X, pady=(0, 10))
        
        end_default = datetime.now().date()
        start_default = end_default - timedelta(days=30)
        
        ttk.Label(dateentry_frame, text="Start Date:").pack(side=tk.LEFT)
        start_date_picker = DateEntry(dateentry_frame, width=12, background='darkblue',
                                     foreground='white', borderwidth=2)
        start_date_picker.set_date(start_default)
        start_date_picker.pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(dateentry_frame, text="End Date:").pack(side=tk.LEFT)
        end_date_picker = DateEntry(dateentry_frame, width=12, background='darkblue',
                                   foreground='white', borderwidth=2)
        end_date_picker.set_date(end_default)
        end_date_picker.pack(side=tk.LEFT, padx=(5, 10))
        
        def test_dateentry():
            start_val = start_date_picker.get_date()
            end_val = end_date_picker.get_date()
            result_label.config(text=f"DateEntry: {start_val} to {end_val}")
        
        ttk.Button(dateentry_frame, text="Test DateEntry", command=test_dateentry).pack(side=tk.LEFT, padx=(10, 0))
        
        print("✅ DateEntry widgets created successfully")
        
    except Exception as e:
        print(f"❌ DateEntry creation failed: {e}")
        error_frame = ttk.LabelFrame(main_frame, text="DateEntry Error", padding=10)
        error_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(error_frame, text=f"Error: {str(e)}", foreground="red").pack()
    
    # Result display
    result_frame = ttk.Frame(main_frame)
    result_frame.pack(fill=tk.X, pady=10)
    
    ttk.Label(result_frame, text="Result:", font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
    result_label = ttk.Label(result_frame, text="Click a test button", foreground="blue")
    result_label.pack(side=tk.LEFT, padx=(10, 0))
    
    # Instructions
    instructions = ttk.Label(main_frame, 
                           text="🎯 Both date picker methods should be visible above.\n"
                           "If DateEntry widgets are not visible, there may be a tkcalendar issue.",
                           font=('Arial', 10), foreground="green")
    instructions.pack(pady=10)
    
    print("🎯 Test window created. Both picker types should be visible...")
    root.mainloop()

if __name__ == "__main__":
    minimal_date_picker_test()