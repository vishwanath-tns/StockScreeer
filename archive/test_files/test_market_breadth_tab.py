"""
Test Market Breadth Tab Directly

This script tests the Market Breadth tab in isolation to see
if the date dropdown now works correctly.
"""
import sys
import os
sys.path.append('d:/MyProjects/StockScreeer')
os.chdir('d:/MyProjects/StockScreeer')

import tkinter as tk
from tkinter import ttk
from gui.tabs.market_breadth import MarketBreadthTab


def test_market_breadth_tab():
    """Test the Market Breadth tab directly."""
    print("🧪 Testing Market Breadth Tab...")
    
    # Create test window
    root = tk.Tk()
    root.title("Market Breadth Tab Test")
    root.geometry("1200x800")
    
    # Create the Market Breadth tab
    print("🔧 Creating Market Breadth tab...")
    tab = MarketBreadthTab(root)
    tab.pack(fill=tk.BOTH, expand=True)
    
    print("🎮 Market Breadth tab created. Check the dropdown!")
    
    # Add instructions
    def show_combo_values():
        values = tab.date_combo['values']
        current = tab.date_combo.get()
        print(f"📋 Current dropdown values: {values}")
        print(f"📅 Current selection: {current}")
        from tkinter import messagebox
        messagebox.showinfo("Dropdown Status", 
                          f"Values: {len(values)} items\n"
                          f"Options: {list(values)}\n"
                          f"Selected: {current}")
    
    # Add test button
    test_frame = ttk.Frame(root)
    test_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
    
    ttk.Button(test_frame, text="Check Dropdown Values", 
               command=show_combo_values).pack(side=tk.LEFT)
    
    ttk.Label(test_frame, text="Instructions: Click dropdown to see available dates, "
                              "then click 'Check Dropdown Values' to verify",
              foreground="blue").pack(side=tk.LEFT, padx=(20, 0))
    
    root.mainloop()


if __name__ == "__main__":
    test_market_breadth_tab()