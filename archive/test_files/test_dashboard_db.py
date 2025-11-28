#!/usr/bin/env python3
"""
Test database connectivity and table existence for dashboard.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """Test database connection and table existence."""
    try:
        from gui.tabs.dashboard import DashboardTab
        import tkinter as tk
        from dotenv import load_dotenv
        from sqlalchemy import create_engine, text
        
        load_dotenv()
        
        # Get database credentials
        MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
        MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
        MYSQL_DB = os.getenv('MYSQL_DB', 'stocks')
        MYSQL_USER = os.getenv('MYSQL_USER', 'root')
        MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'password')
        
        print(f"Testing connection to: {MYSQL_USER}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}")
        
        # Create engine
        engine = create_engine(
            f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4',
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        # Test connection and check tables
        with engine.connect() as conn:
            print("✅ Database connection successful")
            
            # Check what tables exist
            result = conn.execute(text("SHOW TABLES"))
            all_tables = [row[0] for row in result]
            print(f"Found {len(all_tables)} tables total")
            
            # Check for specific tables
            target_tables = ['nse_equity_bhavcopy_full', 'moving_averages', 'nse_rsi_daily', 'trend_analysis']
            
            for table in target_tables:
                if table in all_tables:
                    # Get table info
                    count_result = conn.execute(text(f"SELECT COUNT(*) as cnt FROM {table}"))
                    count = count_result.fetchone().cnt
                    print(f"✅ {table}: {count:,} rows")
                else:
                    print(f"❌ {table}: Table not found")
            
            # List tables containing 'sma' or 'rsi'
            sma_rsi_tables = [t for t in all_tables if 'sma' in t.lower() or 'rsi' in t.lower() or 'moving' in t.lower()]
            if sma_rsi_tables:
                print("\n📊 SMA/RSI related tables found:")
                for table in sma_rsi_tables:
                    print(f"  - {table}")
            else:
                print("\n⚠️  No SMA/RSI related tables found")
                
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_dashboard_status_methods():
    """Test the dashboard status checking methods."""
    try:
        from gui.tabs.dashboard import DashboardTab
        import tkinter as tk
        from dotenv import load_dotenv
        from sqlalchemy import create_engine
        
        load_dotenv()
        
        # Get database credentials
        MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
        MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
        MYSQL_DB = os.getenv('MYSQL_DB', 'stocks')
        MYSQL_USER = os.getenv('MYSQL_USER', 'root')
        MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'password')
        
        # Create engine
        engine = create_engine(
            f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4',
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        # Create a minimal dashboard instance
        root = tk.Tk()
        root.withdraw()  # Hide the window
        frame = tk.Frame(root)
        dashboard = DashboardTab(frame)
        
        print("\n🔍 Testing dashboard status methods:")
        
        # Test each status method
        bhav_status = dashboard.check_bhav_data(engine)
        print(f"BHAV Status: {bhav_status['status']} - {bhav_status.get('details', 'No details')}")
        
        sma_status = dashboard.check_sma_data(engine)
        print(f"SMA Status: {sma_status['status']} - {sma_status.get('details', 'No details')}")
        
        rsi_status = dashboard.check_rsi_data(engine)
        print(f"RSI Status: {rsi_status['status']} - {rsi_status.get('details', 'No details')}")
        
        trend_status = dashboard.check_trend_data(engine)
        print(f"Trend Status: {trend_status['status']} - {trend_status.get('details', 'No details')}")
        
        # Clean up
        root.destroy()
        print("✅ Dashboard status methods test completed")
        return True
        
    except Exception as e:
        print(f"❌ Dashboard status methods test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🔍 Testing Dashboard Database Integration")
    print("=" * 50)
    
    test1_passed = test_database_connection()
    test2_passed = test_dashboard_status_methods()
    
    print("\n" + "=" * 50)
    if test1_passed and test2_passed:
        print("🎉 All tests passed! Dashboard should work correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)