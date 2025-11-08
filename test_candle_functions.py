"""Test weekly and monthly candle functions specifically."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_candle_functions():
    """Test the weekly and monthly candle functions."""
    try:
        from db.trends_repo import get_weekly_candle, get_monthly_candle
        import reporting_adv_decl as rad
        
        print("Testing weekly and monthly candle functions...")
        
        # Get database engine
        engine = rad.engine()
        
        # Test with a common symbol
        test_symbol = "RELIANCE"
        test_date = "2025-11-06"
        
        print(f"Testing with symbol: {test_symbol}, date: {test_date}")
        
        # Test weekly candle
        print("1. Testing get_weekly_candle...")
        weekly_result = get_weekly_candle(engine, test_symbol, test_date)
        print(f"   Weekly candle result: {weekly_result}")
        
        # Test monthly candle
        print("2. Testing get_monthly_candle...")
        monthly_result = get_monthly_candle(engine, test_symbol, test_date)
        print(f"   Monthly candle result: {monthly_result}")
        
        print("\n✅ Candle function tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_candle_functions()