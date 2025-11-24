"""
Check Intraday Data Status
===========================
Verifies if 1-minute intraday data is present in the database
"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv()

def create_db_engine():
    """Create database engine"""
    url = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        database=os.getenv('MYSQL_DB', 'marketdata'),
        query={"charset": "utf8mb4"}
    )
    return create_engine(url, pool_pre_ping=True)

def check_intraday_data():
    """Check status of intraday data"""
    engine = create_db_engine()
    
    print("=" * 80)
    print("INTRADAY DATA STATUS CHECK")
    print("=" * 80)
    
    # Check if tables exist
    print("\n1. Checking if intraday tables exist...")
    print("-" * 80)
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT TABLE_NAME, TABLE_ROWS, CREATE_TIME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME LIKE 'intraday%'
            ORDER BY TABLE_NAME
        """))
        
        tables = result.fetchall()
        
        if not tables:
            print("❌ No intraday tables found!")
            print("\n💡 Run this to create tables:")
            print("   python realtime_market_breadth/create_intraday_tables.py")
            return False
        
        print(f"\n✅ Found {len(tables)} intraday table(s):")
        for table_name, row_count, create_time in tables:
            print(f"   • {table_name:<40} {row_count:>10,} rows (created: {create_time})")
    
    # Check 1-minute candle data
    print("\n2. Checking 1-minute candle data...")
    print("-" * 80)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total_candles,
                COUNT(DISTINCT symbol) as num_symbols,
                COUNT(DISTINCT trade_date) as num_days,
                MIN(trade_date) as earliest_date,
                MAX(trade_date) as latest_date
            FROM intraday_1min_candles
        """))
        
        row = result.fetchone()
        total_candles, num_symbols, num_days, earliest_date, latest_date = row
        
        if total_candles == 0:
            print("❌ NO DATA FOUND in intraday_1min_candles table!")
            print("\n💡 Run this to download 7 days of data:")
            print("   python rebuild_intraday_data.py --days 7")
            return False
        
        print(f"\n✅ Data found:")
        print(f"   Total Candles:    {total_candles:>12,}")
        print(f"   Unique Symbols:   {num_symbols:>12,}")
        print(f"   Trading Days:     {num_days:>12}")
        print(f"   Date Range:       {earliest_date} to {latest_date}")
    
    # Check data by day
    print("\n3. Data breakdown by trading day...")
    print("-" * 80)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                trade_date,
                COUNT(*) as num_candles,
                COUNT(DISTINCT symbol) as num_symbols,
                COUNT(DISTINCT candle_timestamp) as num_unique_times,
                MIN(candle_timestamp) as first_candle,
                MAX(candle_timestamp) as last_candle
            FROM intraday_1min_candles
            GROUP BY trade_date
            ORDER BY trade_date DESC
        """))
        
        rows = result.fetchall()
        
        print(f"\n{'Date':<15} {'Candles':>10} {'Symbols':>10} {'Times':>10} {'First':>20} {'Last':>20}")
        print("-" * 80)
        
        for trade_date, num_candles, num_symbols, num_times, first_candle, last_candle in rows:
            print(f"{trade_date!s:<15} {num_candles:>10,} {num_symbols:>10,} {num_times:>10,} "
                  f"{first_candle.strftime('%H:%M:%S'):>20} {last_candle.strftime('%H:%M:%S'):>20}")
    
    # Check if we have expected 7 days
    print("\n4. Coverage analysis...")
    print("-" * 80)
    
    expected_days = 7
    today = datetime.now().date()
    
    if num_days < expected_days:
        print(f"⚠️  Only {num_days} day(s) of data found (expected {expected_days} days)")
        print(f"   Latest data: {latest_date}")
        days_missing = expected_days - num_days
        print(f"   Missing: {days_missing} day(s)")
    else:
        print(f"✅ {num_days} day(s) of data found")
    
    # Check symbols coverage
    print("\n5. Symbol coverage check...")
    print("-" * 80)
    
    with engine.connect() as conn:
        # Get expected symbols from nse_yahoo_symbol_map
        result = conn.execute(text("""
            SELECT COUNT(*) as total_symbols
            FROM nse_yahoo_symbol_map
            WHERE is_active = 1
        """))
        expected_symbols = result.fetchone()[0]
        
        print(f"   Expected symbols (active): {expected_symbols:>10,}")
        print(f"   Symbols with data:         {num_symbols:>10,}")
        
        if num_symbols < expected_symbols:
            missing = expected_symbols - num_symbols
            print(f"   ⚠️  Missing data for:       {missing:>10,} symbols ({missing/expected_symbols*100:.1f}%)")
        else:
            print(f"   ✅ Coverage: {num_symbols/expected_symbols*100:.1f}%")
    
    # Check advance-decline data
    print("\n6. Advance-Decline snapshots...")
    print("-" * 80)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total_snapshots,
                COUNT(DISTINCT trade_date) as num_days,
                MIN(trade_date) as earliest_date,
                MAX(trade_date) as latest_date
            FROM intraday_advance_decline
        """))
        
        row = result.fetchone()
        total_snapshots, ad_days, ad_earliest, ad_latest = row
        
        if total_snapshots == 0:
            print("⚠️  No advance-decline snapshots found")
            print("   (These are calculated from 1-min candles)")
        else:
            print(f"   Total snapshots:  {total_snapshots:>12,}")
            print(f"   Days covered:     {ad_days:>12}")
            print(f"   Date range:       {ad_earliest} to {ad_latest}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if total_candles == 0:
        print("❌ NO INTRADAY DATA FOUND")
        print("\n📝 To populate the database, run:")
        print("   python rebuild_intraday_data.py --days 7")
    elif num_days < 7:
        print(f"⚠️  INCOMPLETE DATA: Only {num_days} day(s) found (expected 7)")
        print("\n📝 To download missing data, run:")
        print("   python rebuild_intraday_data.py --days 7")
    else:
        print(f"✅ DATA LOOKS GOOD")
        print(f"   {total_candles:,} candles across {num_days} days for {num_symbols} symbols")
    
    print("=" * 80)
    
    engine.dispose()
    return total_candles > 0

if __name__ == "__main__":
    check_intraday_data()
