#!/usr/bin/env python3
"""
Quick test to verify downloaded data and chart compatibility
"""

import sys
import os
sys.path.append('.')
sys.path.append('./yahoo_finance_service')

print("📊 Testing Yahoo Finance Chart Data Access")
print("=" * 50)

def test_data_access():
    """Test data access from the chart visualizer's perspective"""
    try:
        from yahoo_finance_service.db_service import YFinanceDBService
        from datetime import date, timedelta
        
        db_service = YFinanceDBService()
        
        # Get a sample symbol from your data
        conn = db_service.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT symbol FROM yfinance_daily_quotes ORDER BY symbol LIMIT 5")
        symbols = [row[0] for row in cursor.fetchall()]
        
        print(f"✅ Found {len(symbols)} symbols in database")
        print(f"Sample symbols: {symbols}")
        
        if symbols:
            test_symbol = symbols[0]
            print(f"\\n🧪 Testing data for {test_symbol}...")
            
            # Test date range - last 3 months
            end_date = date.today()
            start_date = end_date - timedelta(days=90)
            
            # Use the same method as chart visualizer
            quotes = db_service.get_quotes(test_symbol, start_date, end_date)
            
            print(f"✅ Retrieved {len(quotes)} records for {test_symbol}")
            print(f"Date range: {start_date} to {end_date}")
            
            if quotes:
                sample = quotes[0]
                print(f"Sample record: Date={sample.date}, Close={sample.close}, Volume={sample.volume}")
                
                print("\\n📈 Data is ready for chart visualization!")
                print("\\n🎯 Next steps:")
                print("1. Chart visualizer should be running")
                print(f"2. Select '{test_symbol}' from the symbol dropdown")
                print("3. Choose your preferred date range")
                print("4. Click 'Load Chart' to visualize the data")
                
            else:
                print("❌ No data found for the test period")
                
        cursor.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing data access: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_chart_requirements():
    """Check if all chart dependencies are available"""
    print("\\n🔍 Checking Chart Requirements...")
    
    required_packages = [
        ('matplotlib', 'Plotting library'),
        ('mplfinance', 'Financial charts'),
        ('pandas', 'Data manipulation'),
        ('numpy', 'Numerical computing')
    ]
    
    missing = []
    
    for package, description in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} - {description}")
        except ImportError:
            print(f"❌ {package} - {description} (MISSING)")
            missing.append(package)
    
    if missing:
        print(f"\\n⚠️ Missing packages: {missing}")
        print("Install with: pip install " + " ".join(missing))
        return False
    else:
        print("\\n✅ All chart dependencies are available!")
        return True

def main():
    """Main test function"""
    
    # Test 1: Check requirements
    reqs_ok = check_chart_requirements()
    
    # Test 2: Check data access
    data_ok = test_data_access()
    
    # Summary
    print("\\n" + "=" * 50)
    print("📊 CHART VISUALIZATION READINESS")
    print("=" * 50)
    
    if reqs_ok and data_ok:
        print("🎉 READY FOR CHART VISUALIZATION!")
        print("\\n🚀 Launch commands:")
        print("1. python yahoo_finance_service\\launch_chart_visualizer.py")
        print("2. OR: python yahoo_finance_service\\chart_visualizer.py")
        
    elif not reqs_ok:
        print("❌ Missing required packages - install them first")
        
    elif not data_ok:
        print("❌ Data access issues - check database connection")
        
    else:
        print("❌ Multiple issues detected")

if __name__ == "__main__":
    main()