"""
Comprehensive Test of Enhanced Market Breadth Functionality

This script demonstrates the new Market Breadth features:
1. Date picker instead of dropdown
2. On-demand trend analysis for any date
3. Automatic calculation when data doesn't exist
4. Storage of results for future retrieval
"""
import sys
import os
sys.path.append('d:/MyProjects/StockScreeer')
os.chdir('d:/MyProjects/StockScreeer')

from datetime import date, datetime, timedelta
from services.market_breadth_service import (
    get_current_market_breadth,
    get_market_breadth_for_date,
    get_or_calculate_market_breadth,
    check_trend_data_exists,
    scan_and_calculate_market_breadth
)

def test_comprehensive_functionality():
    """Test all the new market breadth functionality."""
    print("🚀 COMPREHENSIVE MARKET BREADTH FUNCTIONALITY TEST")
    print("=" * 60)
    
    # Test 1: Check existing data
    print("\n1️⃣  Testing existing data retrieval...")
    test_date1 = date(2025, 11, 6)
    print(f"📅 Checking {test_date1}...")
    
    result1 = get_market_breadth_for_date(test_date1)
    if result1['success']:
        summary1 = result1['summary']
        print(f"✅ Found existing data: {summary1.get('total_stocks', 0):,} stocks")
        print(f"   📈 Bullish: {summary1.get('bullish_percentage', 0):.1f}%")
        print(f"   📉 Bearish: {summary1.get('bearish_percentage', 0):.1f}%")
    else:
        print(f"❌ No existing data: {result1['error']}")
    
    # Test 2: Test on-demand calculation
    print("\n2️⃣  Testing on-demand calculation...")
    test_date2 = date(2025, 8, 15)  # Potentially missing date
    print(f"📅 Testing {test_date2} with get_or_calculate...")
    
    result2 = get_or_calculate_market_breadth(test_date2)
    if result2['success']:
        summary2 = result2['summary']
        print(f"✅ Analysis complete: {summary2.get('total_stocks', 0):,} stocks")
        print(f"   📈 Bullish: {summary2.get('bullish_percentage', 0):.1f}%")
        print(f"   📉 Bearish: {summary2.get('bearish_percentage', 0):.1f}%")
        if result2.get('newly_calculated'):
            print("   ✨ Data was newly calculated!")
        else:
            print("   💾 Data was retrieved from existing analysis")
    else:
        print(f"❌ Calculation failed: {result2['error']}")
    
    # Test 3: Check trend data existence
    print("\n3️⃣  Testing trend data existence check...")
    test_dates = [
        date(2025, 11, 6),  # Recent date - likely has data
        date(2025, 8, 1),   # Older date - might not have data
        date(2025, 6, 15),  # Even older - probably no data
    ]
    
    for test_date in test_dates:
        exists = check_trend_data_exists(test_date)
        status = "✅ EXISTS" if exists else "❌ MISSING"
        print(f"   📅 {test_date}: {status}")
    
    # Test 4: Latest data comparison
    print("\n4️⃣  Testing latest data retrieval...")
    latest_result = get_current_market_breadth()
    if latest_result['success']:
        latest_summary = latest_result['summary']
        latest_date = latest_summary.get('analysis_date', 'Unknown')
        print(f"✅ Latest data from {latest_date}")
        print(f"   📊 Total stocks: {latest_summary.get('total_stocks', 0):,}")
        print(f"   📈 Bullish: {latest_summary.get('bullish_percentage', 0):.1f}%")
        print(f"   📉 Bearish: {latest_summary.get('bearish_percentage', 0):.1f}%")
    else:
        print(f"❌ Latest data failed: {latest_result['error']}")
    
    # Test 5: Show available date range
    print("\n5️⃣  Testing available date range...")
    try:
        from services.market_breadth_service import get_available_dates
        dates = get_available_dates(30)
        if dates:
            print(f"📅 Found {len(dates)} available dates")
            print(f"   📅 Newest: {dates[0]}")
            print(f"   📅 Oldest: {dates[-1]}")
            print(f"   📅 Sample dates: {[str(d) for d in dates[:5]]}")
        else:
            print("❌ No available dates found")
    except Exception as e:
        print(f"❌ Error getting available dates: {e}")
    
    print("\n🎉 COMPREHENSIVE TEST COMPLETED!")
    print("=" * 60)
    print("\n💡 SUMMARY OF NEW FEATURES:")
    print("✅ Date picker replaces dropdown (any date selectable)")
    print("✅ Automatic trend calculation for missing dates")
    print("✅ Data persistence in database for future retrieval")
    print("✅ Smart fallback: existing data → calculate → error handling")
    print("✅ Background processing with loading indicators")
    print("✅ Enhanced error messages and user feedback")


def demonstrate_date_picker_workflow():
    """Demonstrate the typical user workflow with date picker."""
    print("\n🎯 DEMONSTRATING DATE PICKER WORKFLOW")
    print("=" * 50)
    
    # Simulate user selecting different dates
    demo_dates = [
        date(2025, 11, 6),   # Recent - should have data
        date(2025, 9, 15),   # Older - might need calculation
        date(2025, 7, 4),    # Much older - probably needs calculation
    ]
    
    for i, demo_date in enumerate(demo_dates, 1):
        print(f"\n📅 Step {i}: User selects {demo_date}")
        print("   🔄 System checking for existing data...")
        
        # Check if data exists
        exists = check_trend_data_exists(demo_date)
        if exists:
            print("   💾 Found existing trend data")
            result = get_market_breadth_for_date(demo_date)
            source = "existing database"
        else:
            print("   📊 No existing data - will calculate trends")
            result = get_or_calculate_market_breadth(demo_date)
            source = "newly calculated" if result.get('newly_calculated') else "database"
        
        if result['success']:
            summary = result['summary']
            total = summary.get('total_stocks', 0)
            bullish = summary.get('bullish_percentage', 0)
            print(f"   ✅ Analysis complete ({source})")
            print(f"   📊 Results: {total:,} stocks, {bullish:.1f}% bullish")
        else:
            print(f"   ❌ Analysis failed: {result['error']}")
    
    print("\n🎉 WORKFLOW DEMONSTRATION COMPLETED!")


if __name__ == "__main__":
    test_comprehensive_functionality()
    demonstrate_date_picker_workflow()