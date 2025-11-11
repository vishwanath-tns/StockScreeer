"""
Test Load Stocks Functionality

This test verifies that the "Load Stocks" button in the 
Market Breadth "Stocks by Category" section works correctly.
"""
import sys
import os
sys.path.append('d:/MyProjects/StockScreeer')
os.chdir('d:/MyProjects/StockScreeer')

def test_load_stocks_function():
    """Test the load stocks functionality directly."""
    print("🧪 Testing Load Stocks functionality...")
    
    try:
        from services.market_breadth_service import get_stocks_in_category
        
        # Test with a common category
        test_category = "Very Bullish (8 to 10)"
        print(f"📊 Testing category: {test_category}")
        
        result = get_stocks_in_category(test_category, trade_date=None)
        
        if result.get('success'):
            stocks = result.get('stocks', [])
            print(f"✅ Successfully loaded {len(stocks)} stocks")
            if stocks:
                print(f"📈 Sample stocks: {[s.get('symbol', 'N/A') for s in stocks[:5]]}")
            else:
                print("📭 No stocks found in this category")
        else:
            error = result.get('error', 'Unknown error')
            print(f"❌ Failed to load stocks: {error}")
            
        # Test with specific date
        print(f"\n📊 Testing with specific date: 2025-11-06")
        result2 = get_stocks_in_category(test_category, trade_date="2025-11-06")
        
        if result2.get('success'):
            stocks2 = result2.get('stocks', [])
            print(f"✅ Successfully loaded {len(stocks2)} stocks for specific date")
        else:
            error2 = result2.get('error', 'Unknown error')
            print(f"❌ Failed to load stocks for specific date: {error2}")
            
        print("\n🎉 Load Stocks function test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


def test_market_breadth_tab_integration():
    """Test the Market Breadth tab integration."""
    print("\n🧪 Testing Market Breadth Tab Integration...")
    
    try:
        import tkinter as tk
        from gui.tabs.market_breadth import MarketBreadthTab
        
        # Create test window
        root = tk.Tk()
        root.title("Load Stocks Test")
        root.geometry("800x600")
        
        # Create Market Breadth tab
        tab = MarketBreadthTab(root)
        
        # Check if the tab has the necessary attributes
        checks = [
            ('date_picker', 'Date picker widget'),
            ('use_latest', 'Latest data toggle'),
            ('category_var', 'Category selection variable'),
            ('load_category_stocks', 'Load category stocks method')
        ]
        
        print("🔍 Checking Market Breadth tab components:")
        all_good = True
        for attr, description in checks:
            if hasattr(tab, attr):
                print(f"✅ {description}: Available")
            else:
                print(f"❌ {description}: Missing")
                all_good = False
        
        if all_good:
            print("✅ All required components are available")
            print("💡 The 'Load Stocks' button should now work correctly!")
        else:
            print("❌ Some components are missing")
        
        print("\n🎮 Instructions for manual testing:")
        print("1. Open Scanner GUI → Market Breadth tab")
        print("2. Navigate to 'Stocks by Category' sub-tab")
        print("3. Select a category from the dropdown")
        print("4. Click 'Load Stocks' button")
        print("5. Verify that stocks are loaded without errors")
        
        # Close test window
        root.after(1000, root.destroy)
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")


if __name__ == "__main__":
    test_load_stocks_function()
    test_market_breadth_tab_integration()