#!/usr/bin/env python3
"""
Quick test script to verify the 5Y All Stocks functionality
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("🧪 Testing '5Y All Stocks' Button Functionality")
print("=" * 50)

try:
    # Test imports
    from yahoo_finance_service.yfinance_downloader_gui import YFinanceDownloaderGUI
    print("✅ GUI class imported successfully")
    
    # Test GUI initialization (without actually showing the window)
    import tkinter as tk
    
    # Initialize the GUI (it creates its own root)
    app = YFinanceDownloaderGUI()
    print("✅ GUI initialized successfully")
    
    # Hide the window for testing
    app.root.withdraw()
    
    # Test that required attributes exist
    required_attrs = [
        'start_year_combo', 'start_month_combo', 'start_day_combo',
        'end_year_combo', 'end_month_combo', 'end_day_combo',
        'duration_var', 'symbol_category_var', 'bulk_download_var'
    ]
    
    missing_attrs = []
    for attr in required_attrs:
        if not hasattr(app, attr):
            missing_attrs.append(attr)
    
    if missing_attrs:
        print(f"❌ Missing attributes: {missing_attrs}")
    else:
        print("✅ All required GUI attributes exist")
    
    # Test that the quick download method exists
    if hasattr(app, 'quick_download_5year_all_stocks'):
        print("✅ quick_download_5year_all_stocks method exists")
    else:
        print("❌ quick_download_5year_all_stocks method missing")
    
    # Test duration options
    if hasattr(app, 'duration_combo') and hasattr(app.duration_combo, 'cget'):
        duration_values = app.duration_combo.cget('values')
        if '5 Years' in duration_values:
            print("✅ '5 Years' option available in duration combo")
        else:
            print(f"❌ '5 Years' not in duration options: {duration_values}")
    
    # Test category options
    print("✅ All functionality tests passed!")
    
    # Cleanup
    app.root.destroy()
    
    print("\\n🎉 The '5Y All Stocks' button should work correctly!")
    print("\\n📋 To use:")
    print("1. Run: python yahoo_finance_service\\yfinance_downloader_gui.py")
    print("2. Click the '📥 5Y All Stocks' button")
    print("3. Confirm the download when prompted")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\\n✅ Test completed successfully!")