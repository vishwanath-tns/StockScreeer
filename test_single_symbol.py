"""Test to reproduce the SQL parameter error."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_analyze_single_symbol():
    """Test analyzing a single symbol to reproduce the error."""
    try:
        from services.trends_service import analyze_symbol_trend
        import reporting_adv_decl as rad
        
        print("Testing analyze_symbol_trend function...")
        
        # Get database engine
        engine = rad.engine()
        
        # Test with one of the symbols that had errors
        test_symbol = "ZENSARTECH"
        test_date = "2025-11-06"
        
        print(f"Testing symbol: {test_symbol}, date: {test_date}")
        
        result = analyze_symbol_trend(test_symbol, test_date, engine)
        print(f"Result: {result}")
        
        print("\n✅ Test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_analyze_single_symbol()