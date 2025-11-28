#!/usr/bin/env python3
"""
Test script for Nifty + Market Breadth chart functionality
"""

import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import text

# Add project path
sys.path.append('d:/MyProjects/StockScreeer')

def test_nifty_breadth_chart_data():
    """Test if we can get Nifty + breadth chart data."""
    print("🧪 Testing Nifty + Market Breadth Chart Data")
    print("=" * 50)
    
    try:
        from services.market_breadth_service import get_nifty_with_breadth_chart_data
        
        # Test with last 30 days
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        print(f"📅 Testing date range: {start_date} to {end_date}")
        
        # Get data
        data = get_nifty_with_breadth_chart_data(start_date, end_date, 'NIFTY 50')
        
        if data.get('success'):
            print("✅ Data retrieval successful!")
            
            nifty_data = data['nifty_data']
            breadth_data = data['breadth_data'] 
            combined_data = data['combined_data']
            
            print(f"\n📊 Data Summary:")
            print(f"   📈 Nifty data: {len(nifty_data)} rows")
            if not nifty_data.empty:
                print(f"       Columns: {list(nifty_data.columns)}")
                print(f"       Date range: {nifty_data['trade_date'].min()} to {nifty_data['trade_date'].max()}")
                if 'close' in nifty_data.columns:
                    print(f"       Price range: {nifty_data['close'].min():.2f} to {nifty_data['close'].max():.2f}")
            
            print(f"   📊 Breadth data: {len(breadth_data)} rows")
            if not breadth_data.empty:
                print(f"       Columns: {list(breadth_data.columns)}")
                print(f"       Date range: {breadth_data['trade_date'].min()} to {breadth_data['trade_date'].max()}")
                avg_bullish = breadth_data['bullish_count'].mean()
                avg_bearish = breadth_data['bearish_count'].mean()
                print(f"       Avg bullish: {avg_bullish:.0f}, Avg bearish: {avg_bearish:.0f}")
            
            print(f"   🔗 Combined data: {len(combined_data)} rows")
            
            # Test chart creation
            print(f"\n📈 Testing chart creation...")
            try:
                import tkinter as tk
                from nifty_breadth_chart import show_nifty_breadth_chart
                
                root = tk.Tk()
                root.withdraw()  # Hide test window
                
                # Create chart window
                chart_window = show_nifty_breadth_chart(root, start_date, end_date)
                print("✅ Chart window created successfully!")
                
                # Close after test
                root.after(1000, root.destroy)
                
                print("🎯 Chart test window ready. Close it to continue...")
                root.mainloop()
                
            except Exception as e:
                print(f"❌ Chart creation failed: {e}")
                import traceback
                traceback.print_exc()
        else:
            error = data.get('error', 'Unknown error')
            print(f"❌ Data retrieval failed: {error}")
            
            # Check what tables exist
            print(f"\n🔍 Checking database tables...")
            try:
                from services.market_breadth_service import get_engine
                engine = get_engine()
                
                with engine.connect() as conn:
                    # Check for indices_daily table
                    result = conn.execute(text("SHOW TABLES LIKE 'indices_daily'"))
                    if result.fetchone():
                        print("✅ indices_daily table exists")
                        
                        # Check for Nifty data
                        result = conn.execute(text("SELECT COUNT(*) as cnt FROM indices_daily WHERE index_name = 'NIFTY 50'"))
                        count = result.fetchone()[0]
                        print(f"   📊 NIFTY 50 records: {count}")
                    else:
                        print("❌ indices_daily table not found")
                    
                    # Check for trend_analysis table
                    result = conn.execute(text("SHOW TABLES LIKE 'trend_analysis'"))
                    if result.fetchone():
                        print("✅ trend_analysis table exists")
                        
                        # Check for recent trend data
                        result = conn.execute(text(f"SELECT COUNT(*) as cnt FROM trend_analysis WHERE trade_date >= '{start_date}'"))
                        count = result.fetchone()[0]
                        print(f"   📊 Recent trend records: {count}")
                    else:
                        print("❌ trend_analysis table not found")
                        
            except Exception as e:
                print(f"❌ Database check failed: {e}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_nifty_breadth_chart_data()