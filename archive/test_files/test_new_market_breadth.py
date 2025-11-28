"""
Test the new Market Breadth functionality with date picker
"""
import sys
import os
sys.path.append('d:/MyProjects/StockScreeer')
os.chdir('d:/MyProjects/StockScreeer')

from services.market_breadth_service import get_or_calculate_market_breadth
from datetime import date, datetime

def test_get_or_calculate():
    """Test the new get_or_calculate_market_breadth function."""
    print("🧪 Testing get_or_calculate_market_breadth function...")
    
    # Test with a recent date that likely has data
    test_date1 = date(2025, 11, 6)
    print(f"\n1. Testing with {test_date1} (likely has data):")
    result1 = get_or_calculate_market_breadth(test_date1)
    
    if result1['success']:
        print(f"✅ Success: {result1['total_analyzed']} stocks analyzed")
        if result1.get('newly_calculated'):
            print("📊 Data was newly calculated")
        else:
            print("💾 Data was retrieved from existing analysis")
    else:
        print(f"❌ Failed: {result1['error']}")
    
    # Test with an older date that might not have data
    test_date2 = date(2025, 9, 15)  # Older date
    print(f"\n2. Testing with {test_date2} (might need calculation):")
    result2 = get_or_calculate_market_breadth(test_date2)
    
    if result2['success']:
        print(f"✅ Success: {result2['total_analyzed']} stocks analyzed")
        if result2.get('newly_calculated'):
            print("📊 Data was newly calculated")
        else:
            print("💾 Data was retrieved from existing analysis")
    else:
        print(f"❌ Failed: {result2['error']}")
    
    print("\n🧪 Test completed!")

if __name__ == "__main__":
    test_get_or_calculate()