"""Test script for the new trend analysis functionality."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_trend_analysis():
    """Test basic trend analysis functionality."""
    print("Testing Trend Analysis Components...")
    
    try:
        # Test imports
        from services.trends_service import determine_candle_trend, calculate_trend_rating
        from db.trends_repo import create_trend_table
        print("✓ All imports successful")
        
        # Test trend determination logic
        print("\nTesting trend determination logic:")
        
        # Test green candle (close > open)
        daily_trend = determine_candle_trend(100.0, 105.0)
        print(f"Green candle (100->105): {daily_trend}")
        assert daily_trend == "UP", f"Expected UP, got {daily_trend}"
        
        # Test red candle (close < open)
        daily_trend = determine_candle_trend(105.0, 100.0)
        print(f"Red candle (105->100): {daily_trend}")
        assert daily_trend == "DOWN", f"Expected DOWN, got {daily_trend}"
        
        # Test doji candle (close = open)
        daily_trend = determine_candle_trend(100.0, 100.0)
        print(f"Doji candle (100->100): {daily_trend}")
        assert daily_trend == "DOWN", f"Expected DOWN, got {daily_trend}"
        
        print("✓ Candle trend determination works correctly")
        
        # Test rating calculation
        print("\nTesting trend rating calculation:")
        
        # All trends UP should give +3
        rating = calculate_trend_rating("UP", "UP", "UP")
        print(f"All UP trends: {rating}")
        assert rating == 3, f"Expected 3, got {rating}"
        
        # All trends DOWN should give -3
        rating = calculate_trend_rating("DOWN", "DOWN", "DOWN")
        print(f"All DOWN trends: {rating}")
        assert rating == -3, f"Expected -3, got {rating}"
        
        # Mixed trends should give appropriate rating
        rating = calculate_trend_rating("UP", "DOWN", "UP")
        print(f"Mixed trends (UP/DOWN/UP): {rating}")
        assert rating == 1, f"Expected 1, got {rating}"
        
        rating = calculate_trend_rating("DOWN", "UP", "DOWN")
        print(f"Mixed trends (DOWN/UP/DOWN): {rating}")
        assert rating == -1, f"Expected -1, got {rating}"
        
        print("✓ Trend rating calculation works correctly")
        
        print("\n✅ All tests passed! The trend analysis system is ready to use.")
        print("\nTo use the trend analysis:")
        print("1. Run the scanner GUI: python scanner_gui.py")
        print("2. Go to the 'Trend Analysis' tab")
        print("3. Click 'Scan Current Day Trends' for today's analysis")
        print("4. Or click 'Scan All Historical Data' for complete backfill")
        print("\nNote: Make sure your .env file has the correct MySQL credentials.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    test_trend_analysis()