#!/usr/bin/env python3
"""
Test script for sectoral analysis date selection functionality.
"""

import sys
import os
from datetime import datetime, timedelta

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.market_breadth_service import get_sectoral_breadth, get_sectoral_analysis_dates

def test_sectoral_dates():
    """Test the get_sectoral_analysis_dates function."""
    print("🔍 Testing sectoral analysis date functionality...")
    print("-" * 60)
    
    try:
        # Test 1: Get available analysis dates
        print("📅 Getting available analysis dates...")
        dates = get_sectoral_analysis_dates()
        
        if dates:
            print(f"✅ Found {len(dates)} available dates:")
            for date in dates[-5:]:  # Show last 5 dates
                print(f"   • {date}")
        else:
            print("❌ No dates found in database")
            return
        
        print()
        
        # Test 2: Test latest date analysis
        print("📊 Testing latest date analysis...")
        latest_result = get_sectoral_breadth("BANKING", use_latest=True)
        
        if latest_result.get('status') == 'success':
            print(f"✅ Latest date analysis successful: {latest_result.get('analysis_date')}")
            print(f"   📈 {latest_result.get('summary', {}).get('total_stocks', 0)} banking stocks analyzed")
        else:
            print(f"❌ Latest date analysis failed: {latest_result.get('message')}")
        
        print()
        
        # Test 3: Test specific date analysis
        if dates:
            test_date = dates[-2] if len(dates) > 1 else dates[0]  # Use second-to-last date
            print(f"📊 Testing specific date analysis: {test_date}")
            
            specific_result = get_sectoral_breadth("BANKING", analysis_date=test_date, use_latest=False)
            
            if specific_result.get('status') == 'success':
                print(f"✅ Specific date analysis successful")
                print(f"   📈 {specific_result.get('summary', {}).get('total_stocks', 0)} banking stocks analyzed")
            else:
                print(f"❌ Specific date analysis failed: {specific_result.get('message')}")
        
        print()
        
        # Test 4: Test invalid date handling
        print("🚫 Testing invalid date handling...")
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        invalid_result = get_sectoral_breadth("BANKING", analysis_date=future_date, use_latest=False)
        
        if invalid_result.get('status') == 'error':
            print(f"✅ Invalid date properly handled: {invalid_result.get('message')}")
        else:
            print(f"❌ Invalid date not properly handled")
        
        print()
        print("🎉 Sectoral analysis date testing completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sectoral_dates()