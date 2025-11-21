#!/usr/bin/env python3
"""
Diagnostic script for 5Y All Stocks feature
Tests the complete flow and provides troubleshooting information
"""

import sys
import os
sys.path.append('.')
sys.path.append('./yahoo_finance_service')

print("🔍 Diagnosing '5Y All Stocks' Feature")
print("=" * 50)

def test_database_connection():
    """Test database connection and symbol data"""
    print("1. Testing database connection...")
    try:
        import mysql.connector
        from yahoo_finance_service.config import YFinanceConfig
        
        conn = mysql.connector.connect(**YFinanceConfig.get_db_config())
        cursor = conn.cursor()
        
        # Test the exact query used by GUI
        query = """
            SELECT nse_symbol, yahoo_symbol, sector 
            FROM nse_yahoo_symbol_map 
            WHERE is_active = 1 AND is_verified = 1
            ORDER BY sector, nse_symbol
        """
        
        cursor.execute(query)
        stocks = cursor.fetchall()
        
        print(f"   ✅ Database connected successfully")
        print(f"   ✅ Found {len(stocks)} verified stock symbols")
        
        if stocks:
            print(f"   ✅ Sample symbols:")
            for i, (nse, yahoo, sector) in enumerate(stocks[:3]):
                print(f"      • {nse} -> {yahoo} ({sector})")
            if len(stocks) > 3:
                print(f"      ... and {len(stocks)-3} more")
        
        cursor.close()
        conn.close()
        return len(stocks)
        
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        return 0

def test_gui_loading():
    """Test GUI symbol loading functionality"""
    print("\\n2. Testing GUI symbol loading...")
    try:
        import tkinter as tk
        from yahoo_finance_service.yfinance_downloader_gui import YFinanceDownloaderGUI
        
        # Create GUI without showing window
        app = YFinanceDownloaderGUI()
        app.root.withdraw()  # Hide window
        
        print("   ✅ GUI initialized successfully")
        
        # Test symbol loading
        print("   🔄 Testing symbol loading...")
        app.symbol_category_var.set("Stocks")
        app.on_category_changed()
        app.load_stock_symbols()
        
        # Check if symbols loaded
        values = app.symbol_combo.cget('values') if hasattr(app.symbol_combo, 'cget') else []
        loaded_count = len(values) if values else 0
        
        if loaded_count > 0:
            print(f"   ✅ GUI loaded {loaded_count} symbols successfully")
            print(f"   ✅ Sample loaded symbols:")
            for i, symbol in enumerate(values[:3]):
                print(f"      • {symbol}")
            if loaded_count > 3:
                print(f"      ... and {loaded_count-3} more")
        else:
            print(f"   ❌ GUI failed to load symbols")
            print(f"   💡 Combo box values: {values}")
        
        app.root.destroy()
        return loaded_count
        
    except Exception as e:
        print(f"   ❌ GUI test error: {e}")
        import traceback
        traceback.print_exc()
        return 0

def test_5y_button_setup():
    """Test if 5Y button setup would work"""
    print("\\n3. Testing 5Y All Stocks button setup...")
    try:
        import tkinter as tk
        from yahoo_finance_service.yfinance_downloader_gui import YFinanceDownloaderGUI
        
        # Create GUI
        app = YFinanceDownloaderGUI()
        app.root.withdraw()
        
        # Test if method exists
        if hasattr(app, 'quick_download_5year_all_stocks'):
            print("   ✅ quick_download_5year_all_stocks method exists")
        else:
            print("   ❌ quick_download_5year_all_stocks method missing")
            
        # Test duration options
        duration_values = app.duration_combo.cget('values')
        if '5 Years' in duration_values:
            print("   ✅ '5 Years' duration option available")
        else:
            print(f"   ❌ '5 Years' not in duration options: {duration_values}")
        
        app.root.destroy()
        return True
        
    except Exception as e:
        print(f"   ❌ 5Y button test error: {e}")
        return False

def main():
    """Run all diagnostic tests"""
    
    # Test 1: Database
    db_symbols = test_database_connection()
    
    # Test 2: GUI Loading 
    gui_symbols = test_gui_loading()
    
    # Test 3: 5Y Button Setup
    button_ready = test_5y_button_setup()
    
    # Summary
    print("\\n" + "=" * 50)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    if db_symbols > 0 and gui_symbols > 0 and button_ready:
        print("✅ ALL TESTS PASSED!")
        print(f"✅ Database has {db_symbols} verified symbols")
        print(f"✅ GUI can load {gui_symbols} symbols")
        print("✅ 5Y All Stocks button should work correctly")
        
        print("\\n🎯 SOLUTION:")
        print("1. Run: python yahoo_finance_service\\yfinance_downloader_gui.py")
        print("2. First click 'Load Stocks' button to load symbols")
        print("3. Then click '📥 5Y All Stocks' button")
        
    elif db_symbols > 0 and gui_symbols == 0:
        print("⚠️  PARTIAL ISSUE DETECTED")
        print(f"✅ Database has {db_symbols} symbols")
        print("❌ GUI failed to load symbols")
        
        print("\\n🔧 SOLUTION:")
        print("1. Run the GUI: python yahoo_finance_service\\yfinance_downloader_gui.py")
        print("2. Manually click 'Load Stocks' button first")
        print("3. If symbols load, then try '📥 5Y All Stocks'")
        print("4. If still fails, restart the GUI and try again")
        
    elif db_symbols == 0:
        print("❌ DATABASE ISSUE DETECTED")
        print("❌ No verified symbols in database")
        
        print("\\n🔧 SOLUTION:")
        print("1. Run symbol verification first:")
        print("   cd D:\\MyProjects\\StockScreeer")
        print("   python verify_all_nse_symbols.py")
        print("2. Then try the 5Y download again")
        
    else:
        print("❌ MULTIPLE ISSUES DETECTED")
        print("🔧 Please check the individual test results above")

if __name__ == "__main__":
    main()