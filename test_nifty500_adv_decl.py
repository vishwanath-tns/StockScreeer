"""
Test script for Nifty 500 Advance-Decline System
"""

import sys
from datetime import date, timedelta
from nifty500_adv_decl_calculator import (
    get_db_engine,
    get_nifty500_symbols,
    compute_date_range,
    get_advance_decline_data
)

def test_database_connection():
    """Test database connection"""
    print("Testing database connection...")
    try:
        from sqlalchemy import text
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            print("✓ Database connection successful")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def test_table_exists():
    """Test if table exists"""
    print("\nTesting table existence...")
    try:
        from sqlalchemy import text
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM nifty500_advance_decline")
            ).fetchone()
            count = result[0]
            print(f"✓ Table exists with {count} records")
            return True
    except Exception as e:
        print(f"✗ Table check failed: {e}")
        return False

def test_nifty500_symbols():
    """Test Nifty 500 symbols loading"""
    print("\nTesting Nifty 500 symbols loading...")
    try:
        symbols = get_nifty500_symbols()
        print(f"✓ Loaded {len(symbols)} Nifty 500 symbols")
        print(f"  Sample: {symbols[:5]}")
        return True
    except Exception as e:
        print(f"✗ Failed to load symbols: {e}")
        return False

def test_yfinance_data():
    """Test Yahoo Finance data availability"""
    print("\nTesting Yahoo Finance data availability...")
    try:
        from sqlalchemy import text
        engine = get_db_engine()
        with engine.connect() as conn:
            # Check Nifty data
            result = conn.execute(text("""
                SELECT COUNT(*), MIN(date), MAX(date)
                FROM yfinance_daily_quotes
                WHERE symbol = 'NIFTY'
            """)).fetchone()
            
            count, min_date, max_date = result
            print(f"✓ Nifty data: {count} records ({min_date} to {max_date})")
            
            if count == 0:
                print("  ⚠️  Warning: No Nifty data found. Please download first.")
                return False
            
            # Check stock data
            result = conn.execute(text("""
                SELECT COUNT(DISTINCT symbol)
                FROM yfinance_daily_quotes
                WHERE symbol != 'NIFTY'
            """)).fetchone()
            
            stock_count = result[0]
            print(f"✓ Stock data: {stock_count} symbols available")
            
            if stock_count < 100:
                print(f"  ⚠️  Warning: Only {stock_count} stocks found. Need 500 for Nifty 500.")
                return False
            
            return True
            
    except Exception as e:
        print(f"✗ Failed to check Yahoo Finance data: {e}")
        return False

def test_computation():
    """Test advance-decline computation"""
    print("\nTesting advance-decline computation (last 5 days)...")
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=10)
        
        print(f"  Computing for {start_date} to {end_date}...")
        stats = compute_date_range(start_date, end_date, force_update=False)
        
        print(f"✓ Computation successful")
        print(f"  Processed: {stats['processed']}")
        print(f"  New entries: {stats['new']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Failed: {stats['failed']}")
        
        return stats['processed'] > 0 or stats['new'] > 0
        
    except Exception as e:
        print(f"✗ Computation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_retrieval():
    """Test data retrieval"""
    print("\nTesting data retrieval...")
    try:
        df = get_advance_decline_data(limit=10)
        
        if df.empty:
            print("  ⚠️  No data retrieved. Compute data first.")
            return False
        
        print(f"✓ Retrieved {len(df)} records")
        print("\n  Latest records:")
        print(df[['trade_date', 'advances', 'declines', 'advance_pct']].head())
        
        return True
        
    except Exception as e:
        print(f"✗ Data retrieval failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("=" * 70)
    print("Nifty 500 Advance-Decline System - Test Suite")
    print("=" * 70)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Table Existence", test_table_exists),
        ("Nifty 500 Symbols", test_nifty500_symbols),
        ("Yahoo Finance Data", test_yfinance_data),
        ("Computation", test_computation),
        ("Data Retrieval", test_data_retrieval),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")
    
    print("=" * 70)
    print(f"Result: {passed}/{total} tests passed")
    print("=" * 70)
    
    if passed == total:
        print("\n✓ All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("1. Compute more historical data:")
        print("   python nifty500_adv_decl_calculator.py --days 180")
        print("\n2. Launch visualizer:")
        print("   python nifty500_adv_decl_visualizer.py")
    else:
        print("\n⚠️  Some tests failed. Please review errors above.")
        if not any(name == "Yahoo Finance Data" and result for name, result in results):
            print("\n📝 Note: You may need to download Yahoo Finance data first.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
