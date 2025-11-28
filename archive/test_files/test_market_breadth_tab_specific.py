#!/usr/bin/env python3
"""
Test Market Breadth tab specifically to debug date range components
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

# Add the project path
sys.path.append('d:/MyProjects/StockScreeer')

def test_market_breadth_tab():
    """Test only the Market Breadth tab"""
    print("🧪 Testing Market Breadth Tab...")
    
    try:
        from gui.tabs.market_breadth import MarketBreadthTab
        print("✅ Market Breadth import successful")
        
        root = tk.Tk()
        root.title("Market Breadth Tab Test")
        root.geometry("1000x700")
        
        # Create the tab
        print("🔄 Creating Market Breadth tab...")
        tab = MarketBreadthTab(root)
        print("✅ Market Breadth tab created")
        
        # Check if date range components exist
        if hasattr(tab, 'start_date_picker'):
            print("✅ Start date picker exists")
        else:
            print("❌ Start date picker missing")
            
        if hasattr(tab, 'end_date_picker'):
            print("✅ End date picker exists")
        else:
            print("❌ End date picker missing")
            
        if hasattr(tab, 'analyze_range_btn'):
            print("✅ Analyze range button exists")
        else:
            print("❌ Analyze range button missing")
        
        print("🎯 Test window ready. Check if date range components are visible...")
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Error during Market Breadth tab test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_market_breadth_tab()