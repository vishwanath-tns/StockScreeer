#!/usr/bin/env python3
"""
Comprehensive test for Market Breadth date range functionality
This script will help identify any remaining visibility issues
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

# Add the project path
sys.path.append('d:/MyProjects/StockScreeer')

def comprehensive_market_breadth_test():
    """Complete test of Market Breadth functionality"""
    print("🧪 Comprehensive Market Breadth Test")
    print("=" * 50)
    
    # Test 1: Import test
    try:
        from gui.tabs.market_breadth import MarketBreadthTab
        from tkcalendar import DateEntry
        print("✅ All imports successful")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return
    
    # Test 2: Create GUI
    root = tk.Tk()
    root.title("Market Breadth - Date Range Test")
    root.geometry("1200x800")
    
    # Create a notebook to simulate the scanner GUI structure
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Create Market Breadth tab
    try:
        print("🔄 Creating Market Breadth tab...")
        market_breadth_frame = ttk.Frame(notebook)
        notebook.add(market_breadth_frame, text="Market Breadth")
        
        # Create the actual tab content
        market_breadth_tab = MarketBreadthTab(market_breadth_frame)
        print("✅ Market Breadth tab created")
        
        # Check components
        components_check = {
            'start_date_picker': hasattr(market_breadth_tab, 'start_date_picker'),
            'end_date_picker': hasattr(market_breadth_tab, 'end_date_picker'),
            'analyze_range_btn': hasattr(market_breadth_tab, 'analyze_range_btn'),
            'range_status_label': hasattr(market_breadth_tab, 'range_status_label')
        }
        
        print("\n📋 Component Check:")
        for component, exists in components_check.items():
            status = "✅" if exists else "❌"
            print(f"   {status} {component}: {'Found' if exists else 'Missing'}")
        
        if all(components_check.values()):
            print("\n🎉 All date range components found!")
            
            # Test functionality
            if hasattr(market_breadth_tab, 'start_date_picker'):
                start_date = market_breadth_tab.start_date_picker.get_date()
                print(f"   📅 Start date: {start_date}")
            
            if hasattr(market_breadth_tab, 'end_date_picker'):
                end_date = market_breadth_tab.end_date_picker.get_date()
                print(f"   📅 End date: {end_date}")
        else:
            print("\n❌ Some components are missing!")
        
    except Exception as e:
        print(f"❌ Failed to create Market Breadth tab: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Add instructions for user
    instruction_frame = ttk.Frame(root)
    instruction_frame.pack(fill=tk.X, padx=10, pady=5)
    
    instructions = ttk.Label(instruction_frame, 
                           text="🎯 Check the Market Breadth tab for date range selection components.\n"
                           "You should see: Start Date picker | End Date picker | 'Analyze Date Range' button",
                           font=('Arial', 10), foreground="blue", justify=tk.CENTER)
    instructions.pack()
    
    print("\n🎯 GUI Test Window Ready!")
    print("   - Navigate to the 'Market Breadth' tab")
    print("   - Look for the 'Market Depth Analysis - Date Range' section")
    print("   - Verify date pickers and button are visible")
    print("   - Close the window when done testing")
    
    root.mainloop()
    print("✅ Test completed")

if __name__ == "__main__":
    comprehensive_market_breadth_test()