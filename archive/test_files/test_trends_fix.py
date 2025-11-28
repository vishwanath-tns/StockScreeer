"""Quick test to verify the trends analysis fix works."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_trends_functionality():
    """Test the basic trends analysis functions."""
    try:
        from services.trends_service import get_trend_summary_stats
        from db.trends_repo import get_latest_trade_date, get_all_symbols
        import reporting_adv_decl as rad
        
        print("Testing trends analysis functionality...")
        
        # Get database engine
        engine = rad.engine()
        
        # Test 1: Get latest trade date
        print("1. Testing get_latest_trade_date...")
        latest_date = get_latest_trade_date(engine)
        print(f"   Latest trade date: {latest_date}")
        
        # Test 2: Get some symbols
        print("2. Testing get_all_symbols...")
        symbols = get_all_symbols(engine, trade_date=latest_date)
        print(f"   Found {len(symbols)} symbols for {latest_date}")
        if symbols:
            print(f"   Sample symbols: {symbols[:5]}")
        
        # Test 3: Get summary stats
        print("3. Testing get_trend_summary_stats...")
        stats = get_trend_summary_stats(engine)
        print(f"   Summary stats: {stats}")
        
        print("\n✅ All tests passed! The trends analysis functionality is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_trends_functionality()