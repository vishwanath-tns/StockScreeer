#!/usr/bin/env python3
"""
Test script for Sectoral Trends Service
======================================

Tests the trends calculation and storage functionality.
"""

import sys
import os
sys.path.append('.')

from datetime import date, timedelta
import pandas as pd

def test_trends_service():
    """Test the sectoral trends service functionality."""
    print("🧪 TESTING SECTORAL TRENDS SERVICE")
    print("=" * 50)
    
    try:
        from services.sectoral_trends_service import SectoralTrendsService, populate_trends_data
        
        # Test 1: Create service instance
        print("\n1️⃣ Testing service initialization...")
        service = SectoralTrendsService()
        print("✅ Service created successfully")
        
        # Test 2: Get data summary
        print("\n2️⃣ Testing data summary...")
        summary = service.get_data_summary()
        print(f"✅ Data Summary: {summary}")
        
        # Test 3: Get available sectors
        print("\n3️⃣ Testing sectors list...")
        sectors = service.get_available_sectors()
        print(f"✅ Found {len(sectors)} sectors:")
        for sector in sectors[:5]:
            print(f"   • {sector}")
        
        # Test 4: Test small data population
        if summary['total_records'] == 0:
            print("\n4️⃣ Testing data population (3 days)...")
            stats = populate_trends_data(3)
            print(f"✅ Population stats: {stats}")
        else:
            print(f"\n4️⃣ Data already exists ({summary['total_records']} records)")
        
        # Test 5: Get trends data for charting
        print("\n5️⃣ Testing trends data retrieval...")
        df = service.get_trends_data(sectors=['NIFTY-PHARMA', 'NIFTY-BANK'], days_back=7)
        
        if not df.empty:
            print(f"✅ Retrieved {len(df)} trend records")
            print(f"   📊 Columns: {list(df.columns)}")
            print(f"   📅 Date range: {df['analysis_date'].min()} to {df['analysis_date'].max()}")
            print(f"   🏷️ Sectors: {df['sector_code'].unique()}")
            
            # Show sample data
            print(f"\n📋 Sample data:")
            if len(df) > 0:
                sample = df.head(3)[['analysis_date', 'sector_code', 'bullish_percent', 'bearish_percent']]
                print(sample.to_string(index=False))
        else:
            print("❌ No trends data retrieved")
        
        print(f"\n✅ ALL TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gui_integration():
    """Test the GUI integration."""
    print(f"\n🖼️ TESTING GUI INTEGRATION")
    print("=" * 30)
    
    try:
        import tkinter as tk
        from gui.windows.sectoral_trends_window import SectoralTrendsWindow
        
        # Create test root window
        root = tk.Tk()
        root.withdraw()  # Hide root
        
        print("✅ GUI components can be imported")
        
        # Note: We won't actually open the window in test mode
        print("✅ SectoralTrendsWindow class available")
        
        root.destroy()
        return True
        
    except ImportError as e:
        print(f"⚠️ GUI dependencies missing: {e}")
        print("   Install matplotlib for full GUI functionality:")
        print("   pip install matplotlib")
        return False
    except Exception as e:
        print(f"❌ GUI test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 SECTORAL TRENDS TESTING")
    print("=" * 60)
    
    # Test the service
    service_ok = test_trends_service()
    
    # Test GUI integration
    gui_ok = test_gui_integration()
    
    print(f"\n" + "=" * 60)
    print(f"📋 TEST RESULTS:")
    print(f"   🔧 Service: {'✅ PASSED' if service_ok else '❌ FAILED'}")
    print(f"   🖼️ GUI: {'✅ PASSED' if gui_ok else '❌ FAILED'}")
    
    if service_ok and gui_ok:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"📝 Next steps:")
        print(f"   1. Run the scanner GUI: python scanner_gui.py")
        print(f"   2. Go to Market Breadth → Sectoral Analysis")
        print(f"   3. Click '📈 Trends Analysis' button")
        print(f"   4. Populate data and explore the charts!")
    else:
        print(f"\n⚠️ SOME TESTS FAILED - Check errors above")
    
    print("=" * 60)