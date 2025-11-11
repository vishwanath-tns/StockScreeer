#!/usr/bin/env python3
"""
Final verification script for Market Breadth date range functionality
"""

import sys
import os
sys.path.append('d:/MyProjects/StockScreeer')

def verify_date_range_functionality():
    """Verify that date range functionality is working"""
    print("🔍 Final Verification of Market Breadth Date Range Functionality")
    print("=" * 65)
    
    # Test 1: Import verification
    print("\n1️⃣ Testing imports...")
    try:
        from gui.tabs.market_breadth import MarketBreadthTab
        from tkcalendar import DateEntry
        from services.market_breadth_service import get_market_depth_analysis_for_range, calculate_market_depth_trends
        print("   ✅ All imports successful")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False
    
    # Test 2: Service function test
    print("\n2️⃣ Testing service functions...")
    try:
        from datetime import datetime, timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        # Test the service function
        range_data = get_market_depth_analysis_for_range(start_date, end_date)
        if range_data.get('success'):
            daily_analysis = range_data.get('daily_analysis', [])
            print(f"   ✅ Date range analysis: {len(daily_analysis)} days analyzed")
            
            # Test trend calculation
            if daily_analysis:
                trend_analysis = calculate_market_depth_trends(daily_analysis)
                print(f"   ✅ Trend analysis: {len(trend_analysis)} metrics calculated")
            else:
                print("   ⚠️ No daily analysis data for trend calculation")
        else:
            print(f"   ❌ Range analysis failed: {range_data.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Service function test failed: {e}")
        return False
    
    # Test 3: GUI component creation test
    print("\n3️⃣ Testing GUI component creation...")
    try:
        import tkinter as tk
        from tkinter import ttk
        
        # Create temporary root
        root = tk.Tk()
        root.withdraw()  # Hide window
        
        # Test frame creation
        test_frame = ttk.Frame(root)
        market_breadth = MarketBreadthTab(test_frame)
        
        # Check components
        components = ['start_date_picker', 'end_date_picker', 'analyze_range_btn', 'range_status_label']
        missing_components = []
        
        for component in components:
            if not hasattr(market_breadth, component):
                missing_components.append(component)
        
        if missing_components:
            print(f"   ❌ Missing components: {missing_components}")
            return False
        else:
            print("   ✅ All GUI components created successfully")
            
        # Test date picker values
        start_date = market_breadth.start_date_picker.get_date()
        end_date = market_breadth.end_date_picker.get_date()
        print(f"   📅 Default date range: {start_date} to {end_date}")
        
        root.destroy()
        
    except Exception as e:
        print(f"   ❌ GUI component test failed: {e}")
        return False
    
    # Summary
    print("\n✅ ALL TESTS PASSED!")
    print("\n📋 Summary:")
    print("   • Date range selection components are properly installed")
    print("   • Service functions for date range analysis are working")
    print("   • GUI components are created without errors")
    print("   • tkcalendar is properly installed and functional")
    print("\n🎯 The Market Breadth tab should now show:")
    print("   • 'Market Depth Analysis - Date Range' section")
    print("   • Start Date and End Date pickers")
    print("   • 'Analyze Date Range' button")
    print("   • Status label for feedback")
    
    return True

if __name__ == "__main__":
    success = verify_date_range_functionality()
    if success:
        print("\n🎉 Verification completed successfully!")
    else:
        print("\n❌ Verification failed. Please check the error messages above.")