#!/usr/bin/env python3
"""
Test the exact flow you're experiencing:
1. Load symbols
2. Click 5Y All Stocks
"""

import sys
import os
sys.path.append('./yahoo_finance_service')

def simulate_your_flow():
    """Simulate exactly what you're doing in the GUI"""
    print("🧪 Simulating Your Exact Flow")
    print("=" * 40)
    
    try:
        import tkinter as tk
        from yfinance_downloader_gui import YFinanceDownloaderGUI
        
        # Create GUI
        app = YFinanceDownloaderGUI()
        app.root.withdraw()  # Hide for testing
        
        print("1. ✅ GUI Created")
        
        # Step 1: Set category to Stocks (like you did)
        app.symbol_category_var.set("Stocks")
        app.on_category_changed()
        print("2. ✅ Set category to 'Stocks'")
        
        # Step 2: Load symbols (like clicking Load Stocks)
        app.load_stock_symbols()
        print("3. ✅ Called load_stock_symbols()")
        
        # Check what happened
        try:
            values = app.symbol_combo.cget('values')
            count = len(values) if values else 0
            print(f"4. ✅ Symbols loaded: {count}")
            
            if count > 0:
                print(f"   Sample symbols: {values[:3]}")
                
                # Step 3: Now test the 5Y method (like clicking 5Y All Stocks)
                print("\\n🚀 Testing '5Y All Stocks' flow...")
                
                # Set the variables like the quick method does
                app.symbol_category_var.set("Stocks")
                app.duration_var.set("5 Years")
                app.bulk_download_var.set(True)
                app.on_bulk_download_changed()
                
                # Check symbol count again
                current_values = app.symbol_combo.cget('values')
                current_count = len(current_values) if current_values else 0
                
                print(f"5. ✅ Symbols still available: {current_count}")
                
                if current_count > 0:
                    print("6. ✅ SUCCESS! 5Y All Stocks should work")
                    print(f"   Ready to download {current_count} symbols for 5 years")
                else:
                    print("6. ❌ PROBLEM: Symbols disappeared after setting bulk mode")
                    
            else:
                print("4. ❌ PROBLEM: No symbols loaded")
                
        except Exception as e:
            print(f"4. ❌ Error checking symbols: {e}")
        
        app.root.destroy()
        
    except Exception as e:
        print(f"❌ Error in simulation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simulate_your_flow()