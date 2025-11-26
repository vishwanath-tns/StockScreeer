"""
Check Data Completeness for All Symbols
Verify that all active symbols have the latest data (25-Nov-2025)
"""
from sync_bhav_gui import engine
from sqlalchemy import text
from datetime import date, timedelta

def check_data_completeness():
    conn = engine().connect()
    
    print("=" * 90)
    print("DATA COMPLETENESS CHECK FOR ALL SYMBOLS")
    print("=" * 90)
    
    # Get expected latest date (yesterday since today market hasn't opened)
    today = date.today()
    expected_latest = today - timedelta(days=1)
    
    print(f"\nExpected Latest Date: {expected_latest}")
    print(f"Today's Date: {today}")
    print(f"Note: Market for {today} opens at 9:15 AM IST\n")
    
    # Get all active symbols from mapping
    result = conn.execute(text("""
        SELECT COUNT(*) as total_active
        FROM nse_yahoo_symbol_map
        WHERE is_active = 1
    """))
    total_active = result.scalar()
    
    print(f"Total Active Symbols in Mapping: {total_active}")
    
    # Get all active symbols and check individually (avoid collation issues)
    result = conn.execute(text("""
        SELECT yahoo_symbol
        FROM nse_yahoo_symbol_map
        WHERE is_active = 1
    """))
    
    active_symbols = [row[0] for row in result.fetchall()]
    
    # Check how many have data for expected latest date
    symbols_with_data = 0
    for symbol in active_symbols:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM yfinance_daily_quotes
            WHERE symbol = :sym AND date = :expected_date
        """), {'sym': symbol, 'expected_date': expected_latest})
        if result.scalar() > 0:
            symbols_with_data += 1
    
    print(f"Symbols with data for {expected_latest}: {symbols_with_data}")
    print(f"Missing data: {total_active - symbols_with_data}")
    
    # Get list of symbols missing latest data (check individually)
    result = conn.execute(text("""
        SELECT nse_symbol, yahoo_symbol, sector
        FROM nse_yahoo_symbol_map
        WHERE is_active = 1
        ORDER BY sector, nse_symbol
    """))
    
    all_symbols = result.fetchall()
    missing_symbols = []
    
    for nse_sym, yahoo_sym, sector in all_symbols:
        result = conn.execute(text("""
            SELECT MAX(date) FROM yfinance_daily_quotes WHERE symbol = :sym
        """), {'sym': yahoo_sym})
        last_date = result.scalar()
        
        if last_date is None or last_date < expected_latest:
            missing_symbols.append((nse_sym, yahoo_sym, sector, last_date))
    
    if missing_symbols:
        print("\n" + "=" * 90)
        print(f"SYMBOLS MISSING DATA FOR {expected_latest}")
        print("=" * 90)
        print(f"\n{'NSE Symbol':<20} {'Yahoo Symbol':<25} {'Sector':<25} {'Last Date':<15}")
        print("-" * 90)
        
        for row in missing_symbols:
            nse_sym, yahoo_sym, sector, last_date = row
            last_date_str = str(last_date) if last_date else 'No Data'
            sector_str = sector if sector else 'N/A'
            print(f"{nse_sym:<20} {yahoo_sym:<25} {sector_str:<25} {last_date_str:<15}")
        
        # Group by reason
        print("\n" + "=" * 90)
        print("ANALYSIS")
        print("=" * 90)
        
        no_data = [row for row in missing_symbols if row[3] is None]
        outdated = [row for row in missing_symbols if row[3] is not None]
        
        print(f"\nSymbols with NO data at all: {len(no_data)}")
        print(f"Symbols with OUTDATED data: {len(outdated)}")
        
        if no_data:
            print(f"\nSymbols with NO DATA:")
            for row in no_data[:10]:  # Show first 10
                print(f"  - {row[0]} ({row[1]})")
            if len(no_data) > 10:
                print(f"  ... and {len(no_data) - 10} more")
    
    else:
        print(f"\n✅ ALL ACTIVE SYMBOLS HAVE LATEST DATA!")
    
    # Check data by symbol type
    print("\n" + "=" * 90)
    print("DATA SUMMARY BY SYMBOL TYPE")
    print("=" * 90)
    
    # Separate indices and stocks
    indices = [sym for sym in active_symbols if sym.startswith('^')]
    stocks = [sym for sym in active_symbols if not sym.startswith('^')]
    
    indices_count = len(indices)
    stocks_total = len(stocks)
    
    # Check indices
    indices_with_data = 0
    for symbol in indices:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM yfinance_daily_quotes
            WHERE symbol = :sym AND date = :expected_date
        """), {'sym': symbol, 'expected_date': expected_latest})
        if result.scalar() > 0:
            indices_with_data += 1
    
    # Check stocks
    stocks_with_data = 0
    for symbol in stocks:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM yfinance_daily_quotes
            WHERE symbol = :sym AND date = :expected_date
        """), {'sym': symbol, 'expected_date': expected_latest})
        if result.scalar() > 0:
            stocks_with_data += 1
    
    print(f"\n{'Type':<15} {'Total':<10} {'With Latest':<15} {'Missing':<10} {'%':<10}")
    print("-" * 90)
    print(f"{'Indices':<15} {indices_count:<10} {indices_with_data:<15} {indices_count - indices_with_data:<10} {(indices_with_data/indices_count*100 if indices_count > 0 else 0):.1f}%")
    print(f"{'Stocks':<15} {stocks_total:<10} {stocks_with_data:<15} {stocks_total - stocks_with_data:<10} {(stocks_with_data/stocks_total*100 if stocks_total > 0 else 0):.1f}%")
    print(f"{'TOTAL':<15} {total_active:<10} {symbols_with_data:<15} {total_active - symbols_with_data:<10} {(symbols_with_data/total_active*100):.1f}%")
    
    # Check overall data statistics
    print("\n" + "=" * 90)
    print("DATABASE STATISTICS")
    print("=" * 90)
    
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT symbol) as unique_symbols,
            MIN(date) as earliest_date,
            MAX(date) as latest_date
        FROM yfinance_daily_quotes
    """))
    
    stats = result.fetchone()
    print(f"\nTotal Records: {stats[0]:,}")
    print(f"Unique Symbols: {stats[1]}")
    print(f"Date Range: {stats[2]} to {stats[3]}")
    print(f"Data Age: {(today - stats[3]).days} days old")
    
    # Latest date record count
    result = conn.execute(text("""
        SELECT COUNT(*) as count
        FROM yfinance_daily_quotes
        WHERE date = :latest_date
    """), {'latest_date': stats[3]})
    
    latest_count = result.scalar()
    print(f"Records for latest date ({stats[3]}): {latest_count:,}")
    
    conn.close()
    
    print("\n" + "=" * 90)

if __name__ == "__main__":
    check_data_completeness()
